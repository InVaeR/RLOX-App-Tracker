using System.Text.Json;
using System.Text.Json.Serialization;

namespace RLOXLauncher;

internal class LauncherConfig
{
    [JsonPropertyName("channel")]
    public string Channel { get; set; } = "stable";

    [JsonPropertyName("checkOnLaunch")]
    public bool CheckOnLaunch { get; set; } = true;

    [JsonPropertyName("autoDownload")]
    public bool AutoDownload { get; set; } = true;

    [JsonPropertyName("autoInstall")]
    public bool AutoInstall { get; set; } = false;

    [JsonPropertyName("checkIntervalHours")]
    public int CheckIntervalHours { get; set; } = 12;

    [JsonPropertyName("skippedVersion")]
    public string? SkippedVersion { get; set; }

    [JsonPropertyName("lastCheckAt")]
    public string? LastCheckAt { get; set; }

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
    };

    public static LauncherConfig Load(string path)
    {
        if (File.Exists(path))
        {
            try
            {
                var json = File.ReadAllText(path);
                return JsonSerializer.Deserialize<LauncherConfig>(json) ?? new LauncherConfig();
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to load launcher config, using defaults", ex);
            }
        }
        return new LauncherConfig();
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
