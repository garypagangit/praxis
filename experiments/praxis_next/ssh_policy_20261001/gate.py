"""Policy decision component only; it performs no network enforcement."""
def decide(ml_warning, transport_protocol, destination_port, in_scope, approved):
    violation=bool(in_scope and transport_protocol==6 and destination_port==22 and not approved)
    return {'warning':bool(ml_warning or violation),'policy_violation':violation,
            'deny_recommended':violation,'reason':'UNAPPROVED_TCP_22' if violation else None}
