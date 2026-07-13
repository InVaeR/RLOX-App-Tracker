using System.Text.RegularExpressions;

namespace RLOXLauncher;

internal readonly struct SemVersion : IComparable<SemVersion>, IEquatable<SemVersion>
{
    private static readonly Regex Pattern = new(
        @"^v?(?<major>\d+)(?:\.(?<minor>\d+))?(?:\.(?<patch>\d+))?" +
        @"(?:-(?<prerelease>[0-9A-Za-z.-]+))?" +
        @"(?:\+(?<build>[0-9A-Za-z.-]+))?$",
        RegexOptions.Compiled);

    public int Major { get; }
    public int Minor { get; }
    public int Patch { get; }
    public string? PreRelease { get; }
    public string? Build { get; }

    private SemVersion(int major, int minor, int patch, string? preRelease, string? build)
    {
        Major = major;
        Minor = minor;
        Patch = patch;
        PreRelease = preRelease;
        Build = build;
    }

    public static bool TryParse(string input, out SemVersion result)
    {
        result = default;
        if (string.IsNullOrEmpty(input)) return false;

        var m = Pattern.Match(input);
        if (!m.Success) return false;

        int major = int.Parse(m.Groups["major"].Value);
        int minor = m.Groups["minor"].Success ? int.Parse(m.Groups["minor"].Value) : 0;
        int patch = m.Groups["patch"].Success ? int.Parse(m.Groups["patch"].Value) : 0;
        string? preRelease = m.Groups["prerelease"].Success ? m.Groups["prerelease"].Value : null;
        string? build = m.Groups["build"].Success ? m.Groups["build"].Value : null;

        result = new SemVersion(major, minor, patch, preRelease, build);
        return true;
    }

    public static SemVersion Parse(string input)
    {
        if (!TryParse(input, out var result))
            throw new FormatException($"Invalid SemVer string: {input}");
        return result;
    }

    public int CompareTo(SemVersion other)
    {
        var majorCmp = Major.CompareTo(other.Major);
        if (majorCmp != 0) return majorCmp;

        var minorCmp = Minor.CompareTo(other.Minor);
        if (minorCmp != 0) return minorCmp;

        var patchCmp = Patch.CompareTo(other.Patch);
        if (patchCmp != 0) return patchCmp;

        if (PreRelease == null && other.PreRelease != null) return 1;
        if (PreRelease != null && other.PreRelease == null) return -1;
        if (PreRelease == null && other.PreRelease == null) return 0;

        return ComparePreRelease(PreRelease!, other.PreRelease!);
    }

    private static int ComparePreRelease(string a, string b)
    {
        var partsA = a.Split('.');
        var partsB = b.Split('.');
        int minLen = Math.Min(partsA.Length, partsB.Length);

        for (int i = 0; i < minLen; i++)
        {
            var cmp = ComparePreReleaseId(partsA[i], partsB[i]);
            if (cmp != 0) return cmp;
        }

        return partsA.Length.CompareTo(partsB.Length);
    }

    private static int ComparePreReleaseId(string a, string b)
    {
        bool aIsNum = int.TryParse(a, out var aNum);
        bool bIsNum = int.TryParse(b, out var bNum);

        if (aIsNum && bIsNum) return aNum.CompareTo(bNum);
        if (aIsNum) return -1;
        if (bIsNum) return 1;

        return string.Compare(a, b, StringComparison.OrdinalIgnoreCase);
    }

    public bool Equals(SemVersion other) => CompareTo(other) == 0;
    public override bool Equals(object? obj) => obj is SemVersion other && Equals(other);
    public override int GetHashCode() => HashCode.Combine(Major, Minor, Patch, PreRelease);

    public override string ToString()
    {
        var v = $"{Major}.{Minor}.{Patch}";
        if (PreRelease != null) v += $"-{PreRelease}";
        if (Build != null) v += $"+{Build}";
        return v;
    }

    public static bool operator >(SemVersion a, SemVersion b) => a.CompareTo(b) > 0;
    public static bool operator <(SemVersion a, SemVersion b) => a.CompareTo(b) < 0;
    public static bool operator >=(SemVersion a, SemVersion b) => a.CompareTo(b) >= 0;
    public static bool operator <=(SemVersion a, SemVersion b) => a.CompareTo(b) <= 0;
    public static bool operator ==(SemVersion a, SemVersion b) => a.Equals(b);
    public static bool operator !=(SemVersion a, SemVersion b) => !a.Equals(b);
}
