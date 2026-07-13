using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows.Forms;

namespace RLOXLauncher;

internal class Program
{
    private const string AppVersion = "2.0.0.0";
    private const string ManifestUrl = "https://github.com/InVaeR/RLOX-App-Tracker/releases/latest/download/latest.json";

    private static void Main(string[] args)
    {
        var opts = ParseArgs(args);

        if (opts.ShowVersion)
        {
            Console.WriteLine($"RLOX Launcher v{AppVersion}");
            return;
        }

        Logger.Init(AppPaths.LauncherLogPath);

        try
        {
            Run(opts).GetAwaiter().GetResult();
        }
        catch (Exception ex)
        {
            Logger.Error("Unhandled exception", ex);
            Environment.ExitCode = 1;
        }
    }

    private static async Task Run(Options opts)
    {
        // --shutdown: send IPC to running app
        if (opts.Shutdown)
        {
            if (ProcessManager.SendIpcCommand("shutdown"))
                Logger.Info("Shutdown command sent");
            else
                Console.Error.WriteLine("App is not running");
            return;
        }

        // --shutdown-for-update: send IPC for graceful shutdown
        if (opts.ShutdownForUpdate)
        {
            if (ProcessManager.SendIpcCommand("shutdown-for-update"))
                Logger.Info("Shutdown-for-update command sent");
            else
                Console.Error.WriteLine("App is not running");
            return;
        }

        // Singleton check
        using var mutex = new Mutex(true, "RLOXAppTracker.Launcher", out var createdNew);
        if (!createdNew && !opts.IgnoreSingleton)
        {
            Logger.Info("Another launcher instance is already running");
            return;
        }

        // Read install state
        var installState = InstallState.Load(AppPaths.InstallJsonPath);
        Logger.Info($"Current version: {installState.CurrentVersion ?? "none"}");

        // --repair: re-check startup marker, purge failed version
        if (opts.Repair)
        {
            HandleRepair(installState);
        }

        // Check startup marker — if current version failed, roll back
        if (!opts.UpdateOnly && installState.CurrentVersion != null)
        {
            var rolledBack = CheckStartupMarkerAndRollback(installState);
            if (rolledBack) installState = InstallState.Load(AppPaths.InstallJsonPath);
        }

        // Clean up old versions (keep only current + previous)
        CleanupOldVersions(installState);

        // --launch or default: if app already running, just activate it
        if (opts.Launch)
        {
            if (ProcessManager.IsAppRunning())
            {
                Logger.Info("App is already running — sending show command");
                ProcessManager.SendIpcCommand("show");
                return;
            }
        }

        // Read launcher config
        var config = LauncherConfig.Load(AppPaths.LauncherConfigPath);

        // Determine whether to check for updates
        var shouldCheck = opts.CheckUpdates
                       || (opts.Launch && config.CheckOnLaunch && ShouldCheck(config))
                       || opts.UpdateOnly;

        if (shouldCheck)
        {
            Logger.Info("Checking for updates...");
            var manifest = await UpdateClient.FetchManifestAsync(ManifestUrl);

            if (manifest != null)
            {
                if (!manifest.IsValid(config.Channel))
                {
                    Logger.Warn("Manifest validation failed — ignoring");
                }
                else
                {
                Logger.Info($"Manifest version: {manifest.Version}, current: {installState.CurrentVersion}");

                var hasUpdate = UpdateManifest.IsNewerVersion(installState.CurrentVersion, manifest.Version);

                if (hasUpdate)
                {
                    Logger.Info($"Update available: {manifest.Version}");

                    config.LastCheckAt = DateTime.Now.ToString("o");
                    config.Save(AppPaths.LauncherConfigPath);

                    var shouldInstall = opts.UpdateOnly; // --update-only always installs

                    if (!shouldInstall && opts.Interactive)
                    {
                        shouldInstall = ShowUpdateDialog(installState.CurrentVersion ?? "unknown", manifest);
                    }

                    if (!shouldInstall && !opts.Interactive && !opts.CheckUpdates)
                    {
                        // --launch with auto-check: respect AutoInstall
                        shouldInstall = config.AutoInstall || manifest.Mandatory;
                    }

                    if (shouldInstall)
                    {
                        var success = await PerformUpdate(manifest, installState, config, opts);
                        if (!success)
                        {
                            Logger.Warn("Update failed — will launch current version if applicable");
                        }
                        else
                        {
                            return; // setup will restart launcher
                        }
                    }
                }
                    else
                    {
                        Logger.Info("No update available");
                        config.LastCheckAt = DateTime.Now.ToString("o");
                        config.Save(AppPaths.LauncherConfigPath);
                    }
                }
            }
        }
        else
        {
            Logger.Warn("Failed to fetch manifest — will launch current version");
        }

        // If --check-updates was used without --launch, don't launch app
        if (opts.CheckUpdates && !opts.Launch)
        {
            Logger.Info("Check complete, not launching (--check-updates without --launch)");
            return;
        }

        // --update-only: don't launch app after update attempt
        if (opts.UpdateOnly)
        {
            return;
        }

        // Launch app (either normal --launch, or fallback after failed update)
        var exePath = installState.GetAppExePath();
        if (exePath == null)
        {
            Logger.Error("No app version found to launch");
            Console.Error.WriteLine("Error: RLOX App Tracker is not installed correctly.");
            Environment.ExitCode = 1;
            return;
        }

        Logger.Info($"Launching app: {exePath}");
        AppLauncher.Launch(exePath, opts.Background, opts.AfterUpdate);
    }

    private static void HandleRepair(InstallState installState)
    {
        var current = installState.CurrentVersion;
        if (current != null)
        {
            var marker = Path.Combine(AppPaths.StateDir, $"startup-ok-{current}");
            if (!File.Exists(marker))
            {
                Logger.Warn($"Repair: startup marker missing for version {current}");
                var prev = installState.PreviousVersion;
                if (prev != null)
                {
                    Logger.Info($"Repair: rolling back to {prev}");
                    installState.CurrentVersion = prev;
                    installState.PreviousVersion = null;
                    installState.AppExecutable = $"versions\\{installState.CurrentVersion}\\RLOXAppTracker.exe";
                    installState.Save(AppPaths.InstallJsonPath);
                }
            }
            else
            {
                Logger.Info("Repair: startup marker OK");
            }
        }
    }

    /// <summary>
    /// Checks startup-ok marker for the current version.
    /// If missing, the previous launch failed — roll back to previous version.
    /// </summary>
    private static bool CheckStartupMarkerAndRollback(InstallState installState)
    {
        var current = installState.CurrentVersion;
        if (current == null) return false;

        var marker = Path.Combine(AppPaths.StateDir, $"startup-ok-{current}");
        if (!File.Exists(marker))
        {
            Logger.Warn($"Startup marker not found for version {current} — possible crash");

            var prev = installState.PreviousVersion;
            if (prev != null)
            {
                Logger.Info($"Rolling back to version {prev}");

                var prevExe = Path.Combine(AppPaths.VersionsDir, prev, "RLOXAppTracker.exe");
                if (File.Exists(prevExe))
                {
                    installState.CurrentVersion = prev;
                    installState.PreviousVersion = null;
                    installState.AppExecutable = $"versions\\{installState.CurrentVersion}\\RLOXAppTracker.exe";
                    installState.Save(AppPaths.InstallJsonPath);
                    Logger.Info($"Rolled back to version {installState.CurrentVersion}");
                    return true;
                }

                Logger.Warn("Previous version files not found, cannot roll back");
            }
            else
            {
                Logger.Warn("No previous version to roll back to");
            }
        }
        return false;
    }

    /// <summary>
    /// Removes version directories older than the current and previous versions.
    /// </summary>
    private static void CleanupOldVersions(InstallState installState)
    {
        var versionsDir = AppPaths.VersionsDir;
        if (!Directory.Exists(versionsDir)) return;

        var keep = new HashSet<string>();
        if (installState.CurrentVersion != null)
            keep.Add(installState.CurrentVersion);
        if (installState.PreviousVersion != null)
            keep.Add(installState.PreviousVersion);

        foreach (var dir in Directory.GetDirectories(versionsDir))
        {
            var versionName = Path.GetFileName(dir);
            if (!keep.Contains(versionName))
            {
                try
                {
                    Directory.Delete(dir, true);
                    Logger.Info($"Removed old version: {versionName}");
                }
                catch (Exception ex)
                {
                    Logger.Warn($"Failed to remove old version {versionName}: {ex.Message}");
                }
            }
        }
    }

    private static async Task<bool> PerformUpdate(UpdateManifest manifest, InstallState installState, LauncherConfig config, Options opts)
    {
        // Download installer
        Logger.Info("Downloading installer...");
        var setupPath = await UpdateClient.DownloadInstallerAsync(
            manifest.Installer!.Url!,
            Path.Combine(AppPaths.UpdatesDir, "downloads"),
            manifest.Installer.Size,
            manifest.Installer.Sha256!);

        if (setupPath == null)
        {
            Logger.Error("Download failed — aborting update");
            if (opts.Interactive)
                Console.Error.WriteLine("Download failed. Check logs for details.");
            return false;
        }

        // Send IPC shutdown to app
        var appPid = ProcessManager.GetAppProcessId();
        if (appPid.HasValue)
        {
            Logger.Info("Sending shutdown-for-update to app");
            if (!ProcessManager.SendIpcCommand("shutdown-for-update"))
            {
                Logger.Warn("IPC shutdown failed, will kill process");
            }
            ProcessManager.WaitForProcessExit(appPid, 10000);
            if (ProcessManager.IsAppRunning())
            {
                Logger.Warn("App still running — killing");
                ProcessManager.KillProcess(appPid);
            }
        }

        // Run installer
        Logger.Info("Running installer...");
        var started = UpdateInstaller.RunInstaller(setupPath);
        if (!started)
        {
            Logger.Error("Failed to start installer");
            return false;
        }

        // Launcher will exit — the installer will launch the new launcher
        Logger.Info("Setup started, exiting launcher");
        return true;
    }

    private static bool ShouldCheck(LauncherConfig config)
    {
        if (config.LastCheckAt == null) return true;
        if (config.CheckIntervalHours <= 0) return true;

        if (DateTime.TryParse(config.LastCheckAt, out var lastCheck))
        {
            return (DateTime.Now - lastCheck).TotalHours >= config.CheckIntervalHours;
        }
        return true;
    }

    private static bool ShowUpdateDialog(string currentVersion, UpdateManifest manifest)
    {
        var msg = $"Current version: {currentVersion}\n" +
                  $"New version: {manifest.Version}\n" +
                  $"Size: {FormatSize(manifest.Installer?.Size ?? 0)}\n" +
                  $"Published: {manifest.PublishedAt ?? "unknown"}\n";

        if (manifest.Mandatory)
            msg += "\nThis is a mandatory update.";

        var caption = "Update Available — RLOX App Tracker";
        var buttons = manifest.Mandatory
            ? MessageBoxButtons.OK
            : MessageBoxButtons.YesNo;

        var result = MessageBox.Show(msg, caption, buttons, MessageBoxIcon.Information);
        return result == DialogResult.Yes || result == DialogResult.OK;
    }

    private static string FormatSize(long bytes)
    {
        if (bytes < 1024) return $"{bytes} B";
        if (bytes < 1024 * 1024) return $"{bytes / 1024.0:F1} KB";
        if (bytes < 1024 * 1024 * 1024) return $"{bytes / (1024.0 * 1024):F1} MB";
        return $"{bytes / (1024.0 * 1024 * 1024):F1} GB";
    }

    private static Options ParseArgs(string[] args)
    {
        var opts = new Options();
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i].ToLowerInvariant())
            {
                case "--launch":
                    opts.Launch = true;
                    break;
                case "--background":
                    opts.Background = true;
                    break;
                case "--check-updates":
                    opts.CheckUpdates = true;
                    break;
                case "--interactive":
                    opts.Interactive = true;
                    break;
                case "--silent":
                    opts.Interactive = false;
                    break;
                case "--repair":
                    opts.Repair = true;
                    break;
                case "--shutdown":
                    opts.Shutdown = true;
                    break;
                case "--shutdown-for-update":
                    opts.ShutdownForUpdate = true;
                    break;
                case "--update-only":
                    opts.UpdateOnly = true;
                    break;
                case "--after-update":
                    opts.AfterUpdate = true;
                    break;
                case "--version":
                    opts.ShowVersion = true;
                    break;
                case "--ignore-singleton":
                    opts.IgnoreSingleton = true;
                    break;
            }
        }
        return opts;
    }

    private class Options
    {
        public bool Launch { get; set; }
        public bool Background { get; set; }
        public bool CheckUpdates { get; set; }
        public bool Interactive { get; set; }
        public bool Repair { get; set; }
        public bool Shutdown { get; set; }
        public bool ShutdownForUpdate { get; set; }
        public bool UpdateOnly { get; set; }
        public bool AfterUpdate { get; set; }
        public bool ShowVersion { get; set; }
        public bool AutoCheck { get; set; }
        public bool IgnoreSingleton { get; set; }
    }
}

/// <summary>
/// Represents the install.json state file.
/// </summary>
internal class InstallState
{
    [JsonPropertyName("schemaVersion")]
    public int SchemaVersion { get; set; }

    [JsonPropertyName("currentVersion")]
    public string? CurrentVersion { get; set; }

    [JsonPropertyName("previousVersion")]
    public string? PreviousVersion { get; set; }

    [JsonPropertyName("channel")]
    public string? Channel { get; set; }

    [JsonPropertyName("installedAt")]
    public string? InstalledAt { get; set; }

    [JsonPropertyName("appExecutable")]
    public string? AppExecutable { get; set; }

    public static InstallState Load(string path)
    {
        if (File.Exists(path))
        {
            try
            {
                var json = File.ReadAllText(path);
                return JsonSerializer.Deserialize<InstallState>(json) ?? new InstallState();
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to load install state", ex);
            }
        }
        return new InstallState();
    }

    private static readonly JsonSerializerOptions JsonWriteOpts = new()
    {
        WriteIndented = true,
    };

    public void Save(string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (dir != null) Directory.CreateDirectory(dir);
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(this, JsonWriteOpts));
        File.Replace(tmp, path, null);
    }

    public string? GetAppExePath()
    {
        if (AppExecutable != null)
        {
            var fullPath = Path.Combine(AppPaths.InstallDir, AppExecutable);
            if (File.Exists(fullPath)) return fullPath;
        }

        // Fallback: find latest version directory
        return AppLauncher.GetAppExePath(CurrentVersion);
    }
}
