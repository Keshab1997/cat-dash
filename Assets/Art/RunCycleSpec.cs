namespace CatDash.Art
{
    /// <summary>
    /// The animation contract for the Cat Dash cat, frozen by Agent B in batch CD-B1 against
    /// the owner-approved run-cycle reference
    /// <c>docs/art/refs/cat-v2-run-cycle-sheet.png</c>.
    ///
    /// Why this file exists: the CD-B1 brief explicitly says <b>no skinning this batch</b>.
    /// The generated mesh (<c>Assets/Art/Generated/Cat.fbx</c>) is 13 loose, closed islands
    /// (Body, Neck, Head, EyeL, EyeR, Muzzle, EarL/R, LegFrontL/R, LegHindL/R, Tail) and every
    /// island pivot sits on the joint that should drive it, so a 6-bone rigid rig can be added
    /// later without re-topology. Until then this type states what the run cycle needs, so
    /// Agent A (movement) and Agent C (scene wiring) can build against a named contract
    /// instead of guessing, and so the eventual clip can be validated against these numbers.
    ///
    /// This is a specification, not a runtime animator: nothing here plays a clip.
    /// </summary>
    public static class RunCycleSpec
    {
        // ---- Clip ----------------------------------------------------------------
        /// <summary>Exact clip name to author in the Animator / the future Blender action.</summary>
        public const string ClipName = "Run";

        /// <summary>Looping run cycle, 12 frames at 24 fps = 0.5 s = one full stride pair.</summary>
        public const int FrameCount = 12;
        public const int SampleRate = 24;
        public const float LengthSeconds = 0.5f;
        public const bool Loop = true;

        /// <summary>Root motion stays OFF: PlayerMover owns forward speed, the clip is in-place.</summary>
        public const bool RootMotion = false;

        // ---- Pose order (source: cat-v2-run-cycle-sheet.png, left to right) -------
        /// <summary>
        /// The four poses of the reference sheet and the order they appear in.
        /// Frozen: the sheet is read left to right as contact, down, up, air, and the
        /// clip must key them in that order so reviewers can compare pose for pose.
        /// </summary>
        public enum RunPose
        {
            Contact = 0,
            Down = 1,
            Up = 2,
            Air = 3,
        }

        public const int PoseCount = 4;

        /// <summary>Pose order as authored, matching the reference sheet.</summary>
        public static readonly RunPose[] PoseOrder =
        {
            RunPose.Contact,
            RunPose.Down,
            RunPose.Up,
            RunPose.Air,
        };

        /// <summary>
        /// Where each pose sits in the loop, as a fraction of one cycle.
        /// The sheet draws the poses evenly spaced, so the clip keys them at even
        /// intervals; only the ORDER is prescribed by the sheet, not the timing feel.
        /// </summary>
        public static readonly float[] PosePhase = { 0.0f, 0.25f, 0.5f, 0.75f };

        /// <summary>Frame each pose should be keyed on (12-frame loop, 3 frames apart).</summary>
        public static int FrameOf(RunPose pose)
        {
            return (int)pose * (FrameCount / PoseCount);
        }

        /// <summary>Loop fraction of a pose (see <see cref="PosePhase"/>).</summary>
        public static float PhaseOf(RunPose pose)
        {
            int index = (int)pose;
            return index >= 0 && index < PosePhase.Length ? PosePhase[index] : 0f;
        }

        // ---- Skeleton (6 bones, rigid weights) -----------------------------------
        /// <summary>Pelvis/root. Bone order is part of the contract; do not reorder.</summary>
        public static readonly string[] BoneNames =
        {
            "Root",       // at the ground between the paws, drives nothing on its own
            "Body",       // mesh islands: Body, Neck
            "Head",       // mesh islands: Head, EyeL, EyeR, Muzzle, EarL, EarR
            "FrontLegs",  // mesh islands: LegFrontL, LegFrontR (legs swing together, rigid)
            "HindLegs",   // mesh islands: LegHindL, LegHindR
            "Tail",       // mesh island: Tail
        };

        public const int BoneCount = 6;

        /// <summary>
        /// Skinning rule for the future rig: each island is weighted 1.0 to the single bone
        /// named above, so the cat stays crisp and low-cost. Islands whose pivot is already at
        /// the joint only need a bind pose, not a re-model.
        /// </summary>
        public const string SkinningRule = "one island = one bone, weight 1.0, no blending, max 4 influences";

        // ---- Run cycle numbers ---------------------------------------------------
        /// <summary>Front/hind leg swing, degrees around the local X axis (pitch).</summary>
        public const float LegSwingDegrees = 28f;

        /// <summary>Hind legs are half a cycle behind the front legs.</summary>
        public const float HindPhaseOffset = 0.5f;

        /// <summary>Left/right legs of a pair are a quarter cycle out of phase for a lively gait.</summary>
        public const float SidePhaseOffset = 0.25f;

        /// <summary>
        /// Vertical body bob in metres: the UPWARD offset above the contact height, reached
        /// twice per stride (mid-stance and the airborne apex). The baseline of
        /// <see cref="BodyBobMetresAt"/> is therefore the contact height, i.e. 0 = lowest
        /// point of the bounce; see that method for the phase convention.
        /// </summary>
        public const float BodyBobMetres = 0.015f;
        public const float BodyBobFrequencyMultiplier = 2f;

        /// <summary>
        /// Values below this (in metres) are snapped to the baseline by
        /// <see cref="BodyBobMetresAt"/>. Chosen far below <see cref="BodyBobMetres"/> and far
        /// above any floating-point residue, so contact positions return exactly 0.
        /// </summary>
        public const float BodyBobContactEpsilon = 1e-6f;

        /// <summary>Tail sway, degrees of side-to-side yaw, lagging the body by an eighth cycle.</summary>
        public const float TailSwayDegrees = 8f;
        public const float TailPhaseLag = 0.125f;

        /// <summary>Head counter-rotation, degrees, keeping the face steady while the body bounds.</summary>
        public const float HeadSteadyDegrees = 2f;

        // ---- Import / transform contract -----------------------------------------
        /// <summary>Exported with axis_forward='-Z', axis_up='Y': the cat faces Unity +Z.</summary>
        public const string ForwardAxis = "+Z";

        /// <summary>
        /// Name of the root GameObject Unity creates when <c>Cat.fbx</c> is imported. Unity
        /// names that root after the FILE, not after the empty root node the generator
        /// exports ("CatDash_Cat"), which is why the part islands are all DESCENDANTS of this
        /// object rather than children of a node called "CatDash_Cat". Asserted on purpose by
        /// ArtContractTests so scene/rig code can rely on the name it has to look up.
        /// </summary>
        public const string ImportedRootName = "Cat";

        /// <summary>Pivot at the ground between the paws; ~0.75 m long, ~0.67 m to the ear tips.</summary>
        public const string PivotNote = "pivot at ground level, centred between the paws; y=0 is the street";

        /// <summary>No animations are embedded in Cat.fbx; the runtime must not expect a clip yet.</summary>
        public const bool HasEmbeddedAnimation = false;

        // ---- Validation helpers --------------------------------------------------
        /// <summary>
        /// Reference pose sampler. Used by tests/tools to check the clip once authored; it is
        /// deliberately stateless so it cannot drift from the constants above.
        /// </summary>
        /// <param name="cycles">Progress through the cycle, 0..1 (values outside wrap).</param>
        /// <param name="phaseOffset">0 for front legs, <see cref="HindPhaseOffset"/> for hind legs.</param>
        /// <returns>Leg pitch in degrees for that cycle position.</returns>
        public static float LegPitchDegrees(float cycles, float phaseOffset)
        {
            float phase = (cycles + phaseOffset) % 1f;
            if (phase < 0f)
            {
                phase += 1f;
            }
            return LegSwingDegrees * (float)System.Math.Sin(phase * 2f * System.Math.PI);
        }

        /// <summary>
        /// Vertical body offset in metres for a cycle position.
        ///
        /// Convention (frozen with this method, documented so A and C can rely on it):
        /// the run cycle dips at each contact and rises at mid-stance and at the airborne
        /// apex, so the value is the UPWARD offset above the contact height —
        /// <c>0</c> at both contacts (cycles 0 and 0.5), <c>+BodyBobMetres</c> at
        /// mid-stance (0.25) and at the apex (0.75). The curve never goes negative.
        ///
        /// This is a raised cosine, not a plain <c>Sin</c>. The earlier Sin version was
        /// wrong in phase (it put the peak on the contacts and the trough at mid-stance)
        /// and, worse, could not be asserted to exact zero: <c>Sin(2 * 2pi * 0.25)</c> is
        /// <c>sin(pi)</c>, which is 1.8e-18 in floating point and failed CI. The small
        /// epsilon snap below keeps the contact positions on the baseline exactly.
        /// </summary>
        public static float BodyBobMetresAt(float cycles)
        {
            float phase = cycles % 1f;
            if (phase < 0f)
            {
                phase += 1f;
            }
            double angle = phase * BodyBobFrequencyMultiplier * 2.0 * System.Math.PI;
            float offset = (float)(BodyBobMetres * ((1.0 - System.Math.Cos(angle)) / 2.0));
            return offset < BodyBobContactEpsilon ? 0f : offset;
        }
    }
}
