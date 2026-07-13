namespace RLOXLauncher;

internal static class UpdateClient
{
    private static readonly HttpClient Client = new()
    {
        Timeout = TimeSpan.FromSeconds(60),
    };

    static UpdateClient()
    {
        Client.DefaultRequestHeaders.UserAgent.ParseAdd("RLOXLauncher/2.0");
    }

    public static async Task<UpdateManifest?> FetchManifestAsync(string url)
    {
        try
        {
            var response = await Client.GetStringAsync(url);
            return UpdateManifest.Parse(response);
        }
        catch (Exception ex)
        {
            Logger.Error($"Failed to fetch manifest: {ex.Message}");
            return null;
        }
    }

    public static async Task<string?> DownloadInstallerAsync(string url, string destDir, long expectedSize, string expectedSha256)
    {
        Directory.CreateDirectory(destDir);
        var tmpPath = Path.Combine(destDir, "setup.exe.part");
        var finalPath = Path.Combine(destDir, "setup.exe");

        try
        {
            Logger.Info($"Downloading: {url}");

            using var response = await Client.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
            response.EnsureSuccessStatusCode();

            var totalBytes = response.Content.Headers.ContentLength ?? -1;
            if (expectedSize > 0 && totalBytes > 0 && totalBytes != expectedSize)
            {
                Logger.Error($"Size mismatch: expected {expectedSize}, got {totalBytes}");
                return null;
            }

            await using var stream = await response.Content.ReadAsStreamAsync();
            await using var fileStream = File.Create(tmpPath);
            await stream.CopyToAsync(fileStream);

            Logger.Info("Download complete, verifying SHA-256");

            if (!HashVerifier.VerifySha256(tmpPath, expectedSha256))
            {
                Logger.Error("SHA-256 mismatch");
                File.Delete(tmpPath);
                return null;
            }

            File.Move(tmpPath, finalPath, overwrite: true);
            Logger.Info($"Installer saved to: {finalPath}");
            return finalPath;
        }
        catch (Exception ex)
        {
            Logger.Error($"Download failed: {ex.Message}");
            try { File.Delete(tmpPath); } catch { }
            return null;
        }
    }
}
