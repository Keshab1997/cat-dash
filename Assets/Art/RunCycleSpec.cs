namespace CatDash.Art
{
    /// <summary>
    /// The animation contract for the Cat Dash cat, frozen by Agent B in batch CD-B1.
    ///
    /// Why this file exists: the CD-B1 brief explicitly says <b>no skinning this batch</b>.
    /// The generated mesh (<c>Assets/Art/Generated/Cat.fbx</c>) is 11 loose, closed islands
    /// (Body, Neck, Head, Muzzle, EarL/R, LegFrontL/R, LegHindL/R, Tail) and every island
    /// pivot sits on the joint that should drive it, so a 6-bone rigid rig can be added
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

        // ---- Skeleton (6 bones, rigid weights) -----------------------------------
        /// <summary>Pelvis/root. Bone order is part of the contract; do not reorder.</summary>
        public static readonly string[] BoneNames =
        {
            "Root",       // at the ground between the paws, drives nothing on its own
            "Body",       // mesh islands: Body, Neck
            "Head",       // mesh islands: Head, Muzzle, EarL, EarR
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

        /// <summary>Vertical body bob in metres, twice per stride (two contacts per cycle).</summary>
        public const float BodyBobMetres = 0.015f;
        public const float BodyBobFrequencyMultiplier = 2f;

        /// <summary>Tail sway, degrees of side-to-side yaw, lagging the body by an eighth cycle.</summary>
        public const float TailSwayDegrees = 8f;
        public const float TailPhaseLag = 0.125f;

        /// <summary>Head counter-rotation, degrees, keeping the face steady while the body bounds.</summary>
        public const float HeadSteadyDegrees = 2f;

        // ---- Import / transform contract -----------------------------------------
        /// <summary>Exported with axis_forward='-Z', axis_up='Y': the cat faces Unity +Z.</summary>
        public const string ForwardAxis = "+Z";

        /// <summary>Model is 1 m to the shoulder, 0.55 m long, pivot at the ground between the paws.</summary>
        public const float PivotNote = "pivot at ground level, centred between the paws; y=0 is the street";

        /// <summary>No animations are embedded in Cat.fbx; the runtime must not expect a clip yet.</summary>
        public const bool HasEmbeddedAnimation = false;

        // ---- Validation helper ---------------------------------------------------
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

        /// <summary>Vertical body offset in metres for a cycle position (see <see cref="BodyBobMetres"/>).</summary>
        public static float BodyBobMetresAt(float cycles)
        {
            float phase = cycles % 1f;
            if (phase < 0f)
            {
                phase += 1f;
            }
            return BodyBobMetres
                   * (float)System.Math.Sin(phase * BodyBobFrequencyMultiplier * 2f * System.Math.PI);
        }
    }
}
