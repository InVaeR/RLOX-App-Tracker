namespace RLOXLauncher;

internal static class AppPaths
{
    private static readonly string LocalAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
    private static readonly string ProductName = "RLOX App Tracker";

    public static string ProductDataDir => Path.Combine(LocalAppData, ProductName);
    public static string ConfigDir => Path.Combine(ProductDataDir, "config");
    public static string LogsDir => Path.Combine(ProductDataDir, "logs");
    public static string UpdatesDir => Path.Combine(ProductDataDir, "updates");
    public static string MigrationDir => Path.Combine(ProductDataDir, "migration");

    public static string LauncherConfigPath => Path.Combine(ConfigDir, "launcher.json");
    public static string AppConfigPath => Path.Combine(ConfigDir, "app.json");
    public static string LauncherLogPath => Path.Combine(LogsDir, "launcher.log");

    public static string InstallDir => Path.Combine(LocalAppData, "Programs", ProductName);
    public static string StateDir => Path.Combine(InstallDir, "state");
    public static string VersionsDir => Path.Combine(InstallDir, "versions");
    public static string InstallJsonPath => Path.Combine(StateDir, "install.json");

    public static string LauncherExePath
    {
        get
        {
            var path = System.Diagnostics.Process.GetCurrentProcess().MainModule?.FileName;
            return path ?? Path.Combine(InstallDir, "RLOXLauncher.exe");
        }
    }
}
