using System.Diagnostics;

namespace RLOXLauncher;

internal static class UpdateInstaller
{
    public static bool RunInstaller(string setupPath)
    {
        if (!File.Exists(setupPath))
        {
            Logger.Error($"Setup not found: {setupPath}");
            return false;
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = setupPath,
                Arguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /UPDATE",
                UseShellExecute = false,
            };

            var proc = Process.Start(psi);
            if (proc == null)
            {
                Logger.Error("Failed to start setup process");
                return false;
            }

            Logger.Info($"Setup started (pid={proc.Id}): {setupPath}");
            return true;
        }
        catch (Exception ex)
        {
            Logger.Error($"Failed to run setup: {ex.Message}");
            return false;
        }
    }
}
