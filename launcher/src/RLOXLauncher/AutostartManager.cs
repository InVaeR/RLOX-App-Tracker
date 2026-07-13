using Microsoft.Win32;

namespace RLOXLauncher;

internal static class AutostartManager
{
    private const string RegistryKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string ValueName = "RLOXAppTracker";

    public static void Enable(string launcherPath)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RegistryKey, writable: true);
            key?.SetValue(ValueName, $"\"{launcherPath}\" --launch --background", RegistryValueKind.String);
            Logger.Info("Autostart enabled");
        }
        catch (Exception ex)
        {
            Logger.Error("Failed to enable autostart", ex);
            throw;
        }
    }

    public static void Disable()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RegistryKey, writable: true);
            if (key?.GetValue(ValueName) != null)
                key.DeleteValue(ValueName);
            Logger.Info("Autostart disabled");
        }
        catch (Exception ex)
        {
            Logger.Error("Failed to disable autostart", ex);
            throw;
        }
    }

    public static bool IsEnabled()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RegistryKey, writable: false);
            return key?.GetValue(ValueName) != null;
        }
        catch
        {
            return false;
        }
    }
}
