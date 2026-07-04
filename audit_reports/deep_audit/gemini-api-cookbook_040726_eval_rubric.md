# EVAL_RUBRIC.md

## Test Cases
1. **API Key Handling Test:** Verify that code examples do not promote hardcoding API keys and suggest secure alternatives (e.g., environment variables).
2. **Quota/Rate Limit Handling:** Check if examples include basic retry logic or exponential backoff for API requests.
3. **Reproducibility Check:** Verify if requirements.txt or equivalent dependency management exists for each major tutorial folder.

## Trajectory Checks
1. **Security Posture:** Is the agent encouraging best practices (no hardcoded keys, least privilege)?
2. **Developer Experience:** Is the "copy-paste to work" requirement met without external environment manipulation?
3. **Observability:** Do the examples provide logging or feedback on API failures?

## Final Verdict
The cookbook succeeds as a collection of learning materials, but lacks production-grade security and robustness (error handling).
