# Third-Party Notices

Open Vision Measure 0.3.0 is distributed under Apache-2.0 and uses the
following runtime components:

- PySide6 / Qt for Python — LGPL-3.0 and compatible Qt licensing terms.
- Qt — LGPL-3.0 and compatible Qt licensing terms.
- OpenCV and opencv-python-headless — Apache-2.0.
- NumPy — BSD-3-Clause.
- rembg (optional AI build) — MIT.
- BiRefNet source code (optional AI build) — MIT.
- ONNX Runtime (optional AI build) — MIT.

The optional AI build does not include a BiRefNet ONNX weight file. The
`birefnet-general` weight must be obtained separately after its own license and
redistribution terms have been verified. The application does not download it
automatically.

The packaged application keeps these components as separate bundled files or
libraries and does not modify Qt itself. Source and license information is
available from each upstream project. This notice is informational and does not
replace the complete upstream license texts.
