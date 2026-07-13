using System.Diagnostics;

namespace RLOXLauncher;

internal static class AppLauncher
{
    public static bool Launch(string appExePath, bool background, bool afterUpdate)
    {
        if (!File.Exists(appExePath))
        {
            Logger.Error($"App executable not found: {appExePath}");
            return false;
        }

        var args = new List<string>();
        if (background) args.Add("--background");
        if (afterUpdate) args.Add("--after-update");

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = appExePath,
                UseShellExecute = false,
            };
            if (args.Count > 0)
                psi.Arguments = string.Join(" ", args);

            var proc = Process.Start(psi);
            if (proc != null)
            {
                Logger.Info($"Launched app: {appExePath} (pid={proc.Id})");
                return true;
            }
            Logger.Error("Process.Start returned null");
            return false;
        }
        catch (Exception ex)
        {
            Logger.Error($"Failed to launch app: {ex.Message}");
            return false;
        }
    }

    public static string? FindLatestVersion()
    {
        var versionsDir = AppPaths.VersionsDir;
        if (!Directory.Exists(versionsDir)) return null;

        var dirs = Directory.GetDirectories(versionsDir);
        if (dirs.Length == 0) return null;

        // Find highest version directory
        var latest = dirs
            .Select(Path.GetFileName)
            .Where(v => !string.IsNullOrEmpty(v) && SemVersion.TryParse(v, out _))
            .OrderByDescending(v => SemVersion.Parse(v!))
            .FirstOrDefault();

        return latest;
    }

    public static string? GetAppExePath(string? version = null)
    {
        version ??= FindLatestVersion();
        if (version == null) return null;

        var exePath = Path.Combine(AppPaths.VersionsDir, version, "RLOXAppTracker.exe");
        return File.Exists(exePath) ? exePath : null;
    }
}
