# Security Policy

## Supported Versions

We actively support the following versions of ManuScan AI with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| 0.9.x   | :x:                |
| < 0.9   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in ManuScan AI, please report it to us privately.

### How to Report

1. **Email**: Send details to security@manuscan-ai.com
2. **Subject**: Include "[SECURITY]" in the subject line
3. **Details**: Provide as much information as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt within 24 hours
- **Initial Assessment**: We'll provide an initial assessment within 72 hours
- **Updates**: We'll keep you informed of our progress
- **Resolution**: We aim to resolve critical issues within 7 days
- **Disclosure**: We'll coordinate public disclosure with you

### Security Best Practices

When using ManuScan AI:

1. **Keep Updated**: Always use the latest version
2. **Secure Deployment**: Follow our deployment security guidelines
3. **Input Validation**: Validate all uploaded files
4. **Access Control**: Implement proper authentication and authorization
5. **Network Security**: Use HTTPS and secure network configurations

### Scope

This security policy covers:
- Core ManuScan AI application
- Official Docker images
- Documentation and examples
- CI/CD pipelines

### Out of Scope

- Third-party dependencies (report to respective maintainers)
- User-specific configurations
- Infrastructure not managed by us

## Security Features

ManuScan AI includes several security features:

### Input Validation
- File type validation
- File size limits
- Malicious content scanning
- Input sanitization

### Data Protection
- No persistent storage of uploaded models
- Temporary file cleanup
- Memory-safe processing
- Secure model inference

### Network Security
- HTTPS enforcement
- CORS configuration
- Rate limiting
- Request validation

### Deployment Security
- Container security scanning
- Dependency vulnerability checks
- Secure defaults
- Security headers

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1**: Acknowledgment sent
3. **Day 3**: Initial assessment completed
4. **Day 7**: Fix developed and tested
5. **Day 14**: Security update released
6. **Day 21**: Public disclosure (if appropriate)

## Security Contact

- **Email**: security@manuscan-ai.com
- **PGP Key**: Available on request
- **Response Time**: 24 hours for acknowledgment

Thank you for helping keep ManuScan AI secure!
