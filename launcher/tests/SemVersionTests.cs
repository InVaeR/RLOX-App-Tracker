using RLOXLauncher;
using Xunit;

namespace RLOXLauncher.Tests;

public class SemVersionTests
{
    [Theory]
    [InlineData("2.0.0", 2, 0, 0, null)]
    [InlineData("2.0.0-dev", 2, 0, 0, "dev")]
    [InlineData("2.0.0-beta.1", 2, 0, 0, "beta.1")]
    [InlineData("v2.0.0", 2, 0, 0, null)]
    [InlineData("1.2.3-alpha+build", 1, 2, 3, "alpha")]
    [InlineData("0.0.1", 0, 0, 1, null)]
    public void TryParse_ValidInput_ReturnsTrue(string input, int major, int minor, int patch, string? preRelease)
    {
        var result = SemVersion.TryParse(input, out var sv);
        Assert.True(result);
        Assert.Equal(major, sv.Major);
        Assert.Equal(minor, sv.Minor);
        Assert.Equal(patch, sv.Patch);
        Assert.Equal(preRelease, sv.PreRelease);
    }

    [Theory]
    [InlineData("")]
    [InlineData("abc")]
    [InlineData("2.0.0.")]
    [InlineData("2.0.0.0")]
    public void TryParse_InvalidInput_ReturnsFalse(string input)
    {
        Assert.False(SemVersion.TryParse(input, out _));
    }

    [Fact]
    public void CompareTo_NewerMajor_ReturnsPositive()
    {
        Assert.True(SemVersion.Parse("2.0.0") > SemVersion.Parse("1.9.9"));
    }

    [Fact]
    public void CompareTo_OlderPatch_ReturnsNegative()
    {
        Assert.True(SemVersion.Parse("2.0.0") < SemVersion.Parse("2.0.1"));
    }

    [Fact]
    public void CompareTo_Equal_ReturnsZero()
    {
        Assert.Equal(0, SemVersion.Parse("2.0.0").CompareTo(SemVersion.Parse("2.0.0")));
    }

    [Fact]
    public void CompareTo_ReleaseGreaterThanPreRelease()
    {
        Assert.True(SemVersion.Parse("2.0.0") > SemVersion.Parse("2.0.0-beta"));
    }

    [Fact]
    public void CompareTo_PreReleaseLessThanRelease()
    {
        Assert.True(SemVersion.Parse("2.0.0-alpha") < SemVersion.Parse("2.0.0"));
    }

    [Fact]
    public void CompareTo_PreReleaseOrder()
    {
        Assert.True(SemVersion.Parse("2.0.0-beta") > SemVersion.Parse("2.0.0-alpha"));
    }

    [Fact]
    public void CompareTo_NumericPreRelease_ComparesNumerically()
    {
        Assert.True(SemVersion.Parse("2.0.0-beta.10") > SemVersion.Parse("2.0.0-beta.2"));
    }

    [Theory]
    [InlineData("2.0.10", "2.0.9", true)]
    [InlineData("2.0.9", "2.0.10", false)]
    [InlineData("2.0.0-dev", "2.0.0", false)]
    [InlineData("2.0.0", "2.0.0-dev", true)]
    public void IsNewerVersion_FromManifest(string candidate, string current, bool expected)
    {
        Assert.Equal(expected, UpdateManifest.IsNewerVersion(current, candidate));
    }
}
