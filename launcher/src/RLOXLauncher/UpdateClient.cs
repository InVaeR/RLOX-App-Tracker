using System.Net;

namespace RLOXLauncher;

internal static class UpdateClient
{
    private const long MaxDownloadSize = 500_000_000; // 500 MB

    private static readonly HttpClient Client = new(new HttpClientHandler
    {
        MaxAutomaticRedirections = 5,
        AllowAutoRedirect = true,
    })
    {
        Timeout = TimeSpan.FromSeconds(120),
    };

    static UpdateClient()
    {
        Client.DefaultRequestHeaders.UserAgent.ParseAdd("RLOXLauncher/2.0");
    }

    public static async Task<UpdateManifest?> FetchManifestAsync(string url)
    {
        if (!IsHttpsUrl(url))
        {
            Logger.Error($"Manifest URL is not HTTPS: {url}");
            return null;
        }

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
        if (!IsHttpsUrl(url))
        {
            Logger.Error($"Download URL is not HTTPS: {url}");
            return null;
        }

        Directory.CreateDirectory(destDir);
        var tmpPath = Path.Combine(destDir, "setup.exe.part");
        var finalPath = Path.Combine(destDir, "setup.exe");

        try
        {
            Logger.Info($"Downloading: {url}");

            using var response = await Client.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
            response.EnsureSuccessStatusCode();

            var contentLength = response.Content.Headers.ContentLength ?? -1;

            if (contentLength > MaxDownloadSize)
            {
                Logger.Error($"Content-Length {contentLength} exceeds maximum {MaxDownloadSize}");
                return null;
            }

            if (expectedSize > 0 && contentLength > 0 && contentLength != expectedSize)
            {
                Logger.Error($"Size mismatch: expected {expectedSize}, got {contentLength}");
                return null;
            }

            await using var stream = await response.Content.ReadAsStreamAsync();
            await using var fileStream = File.Create(tmpPath);

            var buffer = new byte[81920];
            long totalRead = 0;
            int bytesRead;
            while ((bytesRead = await stream.ReadAsync(buffer)) > 0)
            {
                if (totalRead + bytesRead > MaxDownloadSize)
                {
                    Logger.Error("Download exceeded maximum size");
                    fileStream.Close();
                    File.Delete(tmpPath);
                    return null;
                }

                await fileStream.WriteAsync(buffer.AsMemory(0, bytesRead));
                totalRead += bytesRead;
            }

            if (expectedSize > 0 && totalRead != expectedSize)
            {
                Logger.Error($"Size mismatch after download: expected {expectedSize}, got {totalRead}");
                File.Delete(tmpPath);
                return null;
            }

            Logger.Info($"Downloaded {totalRead} bytes, verifying SHA-256");

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

    private static bool IsHttpsUrl(string url)
    {
        return Uri.TryCreate(url, UriKind.Absolute, out var uri)
            && uri.Scheme.Equals("https", StringComparison.OrdinalIgnoreCase);
    }
}
