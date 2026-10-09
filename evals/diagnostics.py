"""Allowlisted error diagnostics: never emit exception messages, URLs or headers."""


def error_details(error):
    chain, seen = [], set()
    while error is not None and id(error) not in seen and len(chain) < 10:
        seen.add(id(error))
        item = {"type": type(error).__name__}
        for field in ("errno", "verify_code", "status_code"):
            value = getattr(error, field, None)
            if type(value) is int:
                item[field] = value
        if type(error).__name__ == "ValidationError" and hasattr(error, "errors"):
            try:
                item["fields"] = [{"location": ".".join(str(part) for part in detail["loc"]),
                                    "type": detail["type"]}
                                   for detail in error.errors(include_url=False, include_input=False)[:5]]
            except (TypeError, KeyError):
                pass
        chain.append(item)
        error = error.__cause__ or error.__context__
    names = {item["type"] for item in chain}
    category, hint = "unknown", "Inspect cause types; no automatic retry was performed."
    if names & {"SSLError", "SSLCertVerificationError", "CertificateError"}:
        category, hint = "tls", "Check certificate trust and TLS interception; do not disable certificate verification."
    elif "gaierror" in names:
        category, hint = "dns", "DNS lookup failed; check DNS/network availability."
    elif names & {"APITimeoutError", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout", "TimeoutError"}:
        category, hint = "timeout", "The request timed out; check elapsed time and network/service health. Token limits do not extend timeouts."
    elif names & {"RemoteProtocolError", "ReadError", "WriteError", "ConnectionResetError", "BrokenPipeError"}:
        category, hint = "connection_interrupted", "Connection was interrupted; check network, VPN/proxy and upstream service health."
    elif names & {"ProxyError"}:
        category, hint = "proxy", "Check proxy configuration and connectivity."
    elif names & {"InvalidURL", "UnsupportedProtocol", "LocalProtocolError", "UnicodeEncodeError"}:
        category, hint = "request_configuration", "Inspect endpoint and header configuration locally; do not share keys or raw headers."
    elif names & {"ConnectError", "ConnectionRefusedError", "APIConnectionError"}:
        category, hint = "connection", "Could not complete the connection; check network, firewall, proxy and TLS settings."
    elif names & {"AuthenticationError", "PermissionDeniedError"}:
        category, hint = "access", "Check API key/project access; do not share credentials."
    elif names & {"RateLimitError", "InternalServerError"}:
        category, hint = "service_or_limit", "Check API usage limits and service health before another paid attempt."
    elif "LengthFinishReasonError" in names:
        category, hint = "output_limit", "Model output hit its token cap; prepare a new plan with a higher EVAL_MAX_TOKENS."
    elif names & {"ValidationError", "InvalidCitationIdsError"}:
        category, hint = "response_validation", "A structured model response remained invalid after its bounded retry."
    return {"category": category, "causes": chain, "hint": hint}
