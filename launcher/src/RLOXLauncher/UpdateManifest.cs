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
        if (SemVersion.TryParse(current, out var cur) &&
            SemVersion.TryParse(candidate, out var can))
        {
            return can > cur;
        }
        return false;
    }

    public bool IsValid(string configChannel)
    {
        if (SchemaVersion != 1) return false;
        if (Product != "rlox-app-tracker") return false;
        if (string.IsNullOrEmpty(Version)) return false;
        if (!SemVersion.TryParse(Version, out _)) return false;
        if (Installer == null) return false;
        if (string.IsNullOrEmpty(Installer.Url)) return false;
        if (!Installer.Url.StartsWith("https://", StringComparison.OrdinalIgnoreCase)) return false;
        if (Installer.Size <= 0) return false;
        if (Installer.Size > 500_000_000) return false; // 500 MB max
        if (string.IsNullOrEmpty(Installer.Sha256)) return false;
        if (Installer.Sha256.Length != 64) return false;
        if (!string.IsNullOrEmpty(MinimumLauncherVersion))
        {
            if (!SemVersion.TryParse(MinimumLauncherVersion, out var minLauncher)) return false;
            if (!SemVersion.TryParse(Program.AppVersion, out var launcherVer)) return false;
            if (launcherVer < minLauncher) return false;
        }
        if (!string.IsNullOrEmpty(Channel) && !string.Equals(Channel, configChannel, StringComparison.OrdinalIgnoreCase))
            return false;
        return true;
    }
}
