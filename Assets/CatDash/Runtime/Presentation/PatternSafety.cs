using System;
using CatDash.Gameplay;

namespace CatDash.Presentation
{
    /// <summary>Pure pattern rules: every row must leave a reachable free lane. Owner: CONTENT.</summary>
    public static class PatternSafety
    {
        public const int MaxBlockedPerRow = 2;

        /// <summary>Lanes with no obstacle in the given row.</summary>
        public static Lane[] FreeLanes(Lane[] blockedLanes) { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>True when at least one free lane is reachable from <paramref name="reachableFrom"/> (|step| &lt;= 1).</summary>
        public static bool IsRowSafe(Lane[] blockedLanes, Lane reachableFrom) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
