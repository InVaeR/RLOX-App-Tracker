using System.Text.Json;
using System.Text.Json.Serialization;

namespace RLOXLauncher;

internal class InstallState
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
    };

    [JsonPropertyName("schemaVersion")]
    public int SchemaVersion { get; set; }

    [JsonPropertyName("currentVersion")]
    public string? CurrentVersion { get; set; }

    [JsonPropertyName("previousVersion")]
    public string? PreviousVersion { get; set; }

    [JsonPropertyName("pendingVersion")]
    public string? PendingVersion { get; set; }

    [JsonPropertyName("launchAttemptedAt")]
    public string? LaunchAttemptedAt { get; set; }

    [JsonPropertyName("startupConfirmed")]
    public bool StartupConfirmed { get; set; }

    [JsonPropertyName("channel")]
    public string? Channel { get; set; }

    [JsonPropertyName("installedAt")]
    public string? InstalledAt { get; set; }

    [JsonPropertyName("appExecutable")]
    public string? AppExecutable { get; set; }

    public bool IsValid()
    {
        if (string.IsNullOrEmpty(CurrentVersion)) return false;
        if (!SemVersion.TryParse(CurrentVersion, out _)) return false;
        if (string.IsNullOrEmpty(AppExecutable)) return false;
        return true;
    }

    public string? EffectiveVersion => PendingVersion ?? CurrentVersion;

    public string? GetAppExePath()
    {
        if (AppExecutable != null)
        {
            var fullPath = Path.Combine(AppPaths.InstallDir, AppExecutable);
            if (File.Exists(fullPath)) return fullPath;
        }

        var ver = EffectiveVersion;
        if (ver != null)
        {
            var legacyPath = Path.Combine(AppPaths.VersionsDir, ver, "RLOXAppTracker.exe");
            if (File.Exists(legacyPath)) return legacyPath;
        }

        // Last resort: any installed version
        return AppLauncher.GetAppExePath();
    }

    public static InstallState Load(string path)
    {
        if (File.Exists(path))
        {
            try
            {
                var json = File.ReadAllText(path);
                var state = JsonSerializer.Deserialize<InstallState>(json);
                if (state != null) return state;
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to load install state", ex);
            }
        }
        return new InstallState();
    }

    public void Save(string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (dir != null) Directory.CreateDirectory(dir);
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(this, JsonOpts));
        if (File.Exists(path))
        {
            var backup = path + ".bak";
            File.Replace(tmp, path, backup);
        }
        else
        {
            File.Move(tmp, path);
        }
    }
}
