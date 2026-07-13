using System.Security.Cryptography;

namespace RLOXLauncher;

internal static class HashVerifier
{
    public static string ComputeSha256(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        using var sha256 = SHA256.Create();
        var hash = sha256.ComputeHash(stream);
        return Convert.ToHexStringLower(hash);
    }

    public static bool VerifySha256(string filePath, string expectedHash)
    {
        var actual = ComputeSha256(filePath);
        return string.Equals(actual, expectedHash, StringComparison.OrdinalIgnoreCase);
    }
}
