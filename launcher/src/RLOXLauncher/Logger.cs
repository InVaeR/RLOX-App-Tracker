using System.Diagnostics;

namespace RLOXLauncher;

internal static class Logger
{
    private static string? _logPath;
    private static readonly object Lock = new();

    public static void Init(string path)
    {
        _logPath = path;
        var dir = Path.GetDirectoryName(path);
        if (dir != null) Directory.CreateDirectory(dir);
        Info("=== Launcher started ===");
    }

    public static void Info(string message) => Write("INFO", message);
    public static void Warn(string message) => Write("WARN", message);
    public static void Error(string message) => Write("ERROR", message);
    public static void Error(string message, Exception ex)
    {
        Write("ERROR", $"{message}: {ex.Message}");
        Debug.WriteLine($"{message}: {ex}");
    }

    private static void Write(string level, string message)
    {
        var line = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [{level}] {message}";
        Debug.WriteLine(line);
        lock (Lock)
        {
            if (_logPath != null)
            {
                try
                {
                    File.AppendAllText(_logPath, line + Environment.NewLine);
                }
                catch
                {
                    // ignore
                }
            }
        }
    }
}
