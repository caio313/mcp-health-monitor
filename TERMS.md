# Terms of Use — MCP Health Server

Last updated: March 2026

## 1. Service description

MCP Health Server is a monitoring tool for MCP server ecosystems. It provides health checks, drift detection, and blast radius analysis for services connected by the user.

## 2. Data handling

- Server URLs submitted for monitoring are **never stored in plain text**. All URLs are anonymized using SHA-256 hashing before being persisted.
- Anonymized metrics (latency, availability, drift) are stored to build historical baselines and improve the service.
- No data is sold, shared, or transferred to third parties.

## 3. Use of aggregated data

Anonymized and aggregated metrics may be used to improve the service, generate benchmarks, and develop new features. No individual server URLs or user identities are included in this data.

## 4. No guarantees

The service is provided **"as is"** without warranties of any kind. MCP Health Server does not guarantee uninterrupted availability or accuracy of results.

## 5. Acceptable use

You agree not to use this service to monitor servers you do not own or have explicit permission to monitor.

## 6. Changes

These terms may be updated at any time. Continued use of the service after changes constitutes acceptance of the new terms.

## 7. Contact

For questions about these terms, open an issue on the GitHub repository.
