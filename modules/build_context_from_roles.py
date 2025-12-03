def build_context_from_roles(role_docs: dict) -> str:
    """
    Tổng hợp context cho prompt từ các role.
    Args:
        role_docs: dict {role: [documents]}
    Returns:
        str: context phân loại theo từng role
    """
    context = ""
    for role, docs in role_docs.items():
        if docs:
            context += f"--- {role} ---\n"
            for doc in docs:
                context += f"{doc}\n"
    return context.strip()
