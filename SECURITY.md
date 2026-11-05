# Security Policy

## Supported versions

Security fixes are applied to the latest released minor version and the current
default branch.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose local files,
camera data, credentials, model execution, or arbitrary code execution.

Use the repository's **Security** tab and create a private vulnerability report:

<https://github.com/JinCV0/open-vision-measure/security/advisories/new>

Include the affected version, reproduction steps, impact, and any proposed
mitigation. Avoid attaching unrelated personal files or third-party model
weights.

## Scope notes

- The application is local-first and does not require a remote service.
- AI background removal and model runtimes are not part of the current release.
- Camera and OpenCV failures should be reported as bugs unless they demonstrate
  a security boundary violation.
