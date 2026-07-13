using System.Diagnostics;

namespace RLOXLauncher;

internal static class Logger
{
    private const long MaxLogSize = 2 * 1024 * 1024; // 2 MB
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
                    RotateIfNeeded();
                    File.AppendAllText(_logPath, line + Environment.NewLine);
                }
                catch
                {
                    // ignore
                }
            }
        }
    }

    private static void RotateIfNeeded()
    {
        if (_logPath == null || !File.Exists(_logPath)) return;
        if (new FileInfo(_logPath).Length < MaxLogSize) return;

        for (int i = 3; i >= 1; i--)
        {
            var oldPath = _logPath + "." + i;
            var newPath = _logPath + "." + (i + 1);
            if (File.Exists(oldPath))
            {
                if (i == 3)
                    File.Delete(oldPath);
                else
                    File.Move(oldPath, newPath, overwrite: true);
            }
        }

        File.Move(_logPath, _logPath + ".1", overwrite: true);
    }
}
