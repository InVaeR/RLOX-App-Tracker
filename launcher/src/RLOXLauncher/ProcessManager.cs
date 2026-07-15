using System.Diagnostics;
using System.IO.Pipes;

namespace RLOXLauncher;

internal static class ProcessManager
{
    private const string PipeName = "RLOXAppTracker.Application";

    public static bool SendIpcCommand(string command)
    {
        try
        {
            using var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.Out);
            pipe.Connect(1000);
            using var writer = new StreamWriter(pipe);
            writer.Write(command + "\n");
            writer.Flush();
            return true;
        }
        catch (TimeoutException)
        {
            Logger.Warn("IPC connect timeout — app not running");
            return false;
        }
        catch (Exception ex)
        {
            Logger.Info($"IPC failed (app probably not running): {ex.Message}");
            return false;
        }
    }

    public static bool IsAppRunning()
    {
        var expectedDir = AppPaths.InstallDir;
        foreach (var proc in Process.GetProcessesByName("RLOXAppTracker"))
        {
            try
            {
                var path = proc.MainModule?.FileName;
                if (path != null &&
                    path.StartsWith(expectedDir, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            catch
            {
                return true;
            }
        }
        return false;
    }

    public static int? GetAppProcessId()
    {
        var proc = Process.GetProcessesByName("RLOXAppTracker").FirstOrDefault();
        return proc?.Id;
    }

    public static bool WaitForProcessExit(int? processId, int timeoutMs = 30000)
    {
        if (processId == null) return true;
        try
        {
            var proc = Process.GetProcessById(processId.Value);
            return proc.WaitForExit(timeoutMs);
        }
        catch (ArgumentException)
        {
            return true; // already exited
        }
    }

    public static void KillProcess(int? processId)
    {
        if (processId == null) return;
        try
        {
            var proc = Process.GetProcessById(processId.Value);
            proc.Kill(true);
            proc.WaitForExit(5000);
        }
        catch (ArgumentException) { }
        catch (InvalidOperationException) { }
    }
}
