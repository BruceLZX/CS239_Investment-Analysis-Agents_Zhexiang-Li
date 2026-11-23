"""Run samples FIRST through LAST of one scenario with the translated harness, when the earlier samples already exist.

    python phase2-env/resume_samples.py SIDE CASE FIRST LAST [OUTPUT_DIR]     (from the repository root)

The runner's CLI (`translated_harness.py --sample N`) always runs samples 1 through N and stops at the first sample
directory that exists. This calls the same function the CLI calls for each sample,
policyweave.workbench.runner.run_case, with the harness's own dispatch and assessment, so each sample directory gets
the same files; it then prints the runner's two "Until now" lines.

Used once, on 2026-11-23, for S08 ported samples 3 to 10: the Mac slept with its lid closed (23:31 to 04:02) during
samples 3 and 4, which were set aside outside the repository and not used.
"""
from pathlib import Path
import sys

sys.path[0] = str(Path.cwd())  # as when translated_harness.py runs as a script from the repository root
import translated_harness as harness  # noqa: E402
from policyweave.workbench.runner import print_summary, run_case  # noqa: E402


def main() -> None:
    side, case, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    output = sys.argv[5] if len(sys.argv) > 5 else 'runs'
    for sample in range(first, last + 1):
        run_case(harness._policyweave_dispatch, lambda result: result, side=side, case=case, sample=sample,
                 output=output)
    print_summary(output)


if __name__ == '__main__':
    main()
