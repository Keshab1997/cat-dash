using System.Collections.Generic;
using CatDash.Gameplay;

namespace CatDash.Presentation
{
    /// <summary>Pure pattern rules: every row must leave a reachable free lane. Owner: CONTENT.</summary>
    public static class PatternSafety
    {
        public const int MaxBlockedPerRow = 2;

        /// <summary>Lanes with no obstacle in the given row. Null/empty row = every lane free.</summary>
        public static Lane[] FreeLanes(Lane[] blockedLanes)
        {
            var free = new List<Lane>(Lanes.Count);
            for (int i = 0; i < Lanes.Count; i++)
            {
                Lane lane = (Lane)i;
                if (!Contains(blockedLanes, lane)) free.Add(lane);
            }
            return free.ToArray();
        }

        /// <summary>True when at least one free lane is reachable from <paramref name="reachableFrom"/> (|step| &lt;= 1).</summary>
        public static bool IsRowSafe(Lane[] blockedLanes, Lane reachableFrom)
        {
            Lane[] free = FreeLanes(blockedLanes);
            if (free.Length == 0) return false;

            int from = (int)Lanes.Clamp(reachableFrom);
            for (int i = 0; i < free.Length; i++)
            {
                if (System.Math.Abs((int)free[i] - from) <= 1) return true;
            }
            return false;
        }

        /// <summary>
        /// Copy of a row kept inside the rules: at most <see cref="MaxBlockedPerRow"/> distinct lanes,
        /// never all lanes, sorted Left→Right. Never mutates the input array.
        /// </summary>
        public static Lane[] Sanitize(Lane[] blockedLanes)
        {
            var kept = new List<Lane>(MaxBlockedPerRow);
            if (blockedLanes != null)
            {
                for (int i = 0; i < blockedLanes.Length && kept.Count < MaxBlockedPerRow; i++)
                {
                    Lane lane = Lanes.Clamp(blockedLanes[i]);
                    if (!kept.Contains(lane)) kept.Add(lane);
                }
            }
            // Defensive: even if MaxBlockedPerRow is ever raised, a row must keep one free lane.
            while (kept.Count >= Lanes.Count) kept.RemoveAt(kept.Count - 1);
            kept.Sort();
            return kept.ToArray();
        }

        private static bool Contains(Lane[] lanes, Lane lane)
        {
            if (lanes == null) return false;
            for (int i = 0; i < lanes.Length; i++)
            {
                if (lanes[i] == lane) return true;
            }
            return false;
        }
    }
}
