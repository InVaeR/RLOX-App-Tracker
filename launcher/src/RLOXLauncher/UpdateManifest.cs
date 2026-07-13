using System.Text.Json;
using System.Text.Json.Serialization;

namespace RLOXLauncher;

internal class UpdateManifest
{
    [JsonPropertyName("schemaVersion")]
    public int SchemaVersion { get; set; }

    [JsonPropertyName("product")]
    public string? Product { get; set; }

    [JsonPropertyName("channel")]
    public string? Channel { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("minimumLauncherVersion")]
    public string? MinimumLauncherVersion { get; set; }

    [JsonPropertyName("publishedAt")]
    public string? PublishedAt { get; set; }

    [JsonPropertyName("mandatory")]
    public bool Mandatory { get; set; }

    [JsonPropertyName("installer")]
    public InstallerInfo? Installer { get; set; }

    [JsonPropertyName("releaseNotesUrl")]
    public string? ReleaseNotesUrl { get; set; }

    public class InstallerInfo
    {
        [JsonPropertyName("url")]
        public string? Url { get; set; }

        [JsonPropertyName("sha256")]
        public string? Sha256 { get; set; }

        [JsonPropertyName("size")]
        public long Size { get; set; }
    }

    public static UpdateManifest? Parse(string json)
    {
        try
        {
            var manifest = JsonSerializer.Deserialize<UpdateManifest>(json);
            if (manifest?.SchemaVersion != 1) return null;
            if (manifest?.Product != "rlox-app-tracker") return null;
            if (string.IsNullOrEmpty(manifest.Version)) return null;
            if (manifest.Installer == null) return null;
            if (string.IsNullOrEmpty(manifest.Installer.Url)) return null;
            return manifest;
        }
        catch (JsonException ex)
        {
            Logger.Error("Failed to parse manifest", ex);
            return null;
        }
    }

    public static bool IsNewerVersion(string? current, string? candidate)
    {
        if (string.IsNullOrEmpty(current)) return !string.IsNullOrEmpty(candidate);
        if (string.IsNullOrEmpty(candidate)) return false;
        if (System.Version.TryParse(current.TrimStart('v'), out var cur) &&
            System.Version.TryParse(candidate.TrimStart('v'), out var can))
        {
            return can > cur;
        }
        return string.Compare(candidate, current, StringComparison.OrdinalIgnoreCase) > 0;
    }
}
