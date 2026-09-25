from urllib.parse import urlparse


def _texto(dados, campo, obrigatorio=False):
    valor = dados.get(campo)
    if valor is None:
        if obrigatorio:
            raise ValueError(f'{campo} é obrigatório')
        return ''
    if not isinstance(valor, str) or not valor.strip():
        if obrigatorio:
            raise ValueError(f'{campo} não pode ser vazio')
        return ''
    return valor.strip()


def _url(dados, campo):
    valor = dados.get(campo)
    if valor in (None, ''):
        return None
    if not isinstance(valor, str):
        raise ValueError(f'{campo} deve ser uma URL válida')
    parsed = urlparse(valor)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError(f'{campo} deve ser uma URL válida')
    return valor


def profile_input(dados):
    return {
        'name': _texto(dados, 'name', obrigatorio=True),
        'bio': _texto(dados, 'bio'),
        'avatar_url': _url(dados, 'avatar_url'),
        'github_url': _url(dados, 'github_url'),
        'linkedin_url': _url(dados, 'linkedin_url'),
    }


def technology_input(dados):
    return {
        'name': _texto(dados, 'name', obrigatorio=True),
        'description': _texto(dados, 'description'),
        'icon_url': _url(dados, 'icon_url'),
    }


def project_input(dados):
    profile_id = dados.get('profile_id')
    if not isinstance(profile_id, int) or isinstance(profile_id, bool) or profile_id < 1:
        raise ValueError('profile_id deve ser um inteiro positivo')

    technology_ids = dados.get('technology_ids', [])
    if not isinstance(technology_ids, list) or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in technology_ids
    ):
        raise ValueError('technology_ids deve ser uma lista de inteiros positivos')
    if len(technology_ids) != len(set(technology_ids)):
        raise ValueError('technology_ids não pode conter itens repetidos')

    return {
        'profile_id': profile_id,
        'title': _texto(dados, 'title', obrigatorio=True),
        'description': _texto(dados, 'description'),
        'repository_url': _url(dados, 'repository_url'),
        'demo_url': _url(dados, 'demo_url'),
        'technology_ids': technology_ids,
    }


def feedback_input(dados):
    rating = dados.get('rating')
    if rating is not None and (not isinstance(rating, int) or isinstance(rating, bool) or rating < 1 or rating > 5):
        raise ValueError('rating deve ser um inteiro entre 1 e 5')
    return {
        'author_name': _texto(dados, 'author_name', obrigatorio=True),
        'content': _texto(dados, 'content', obrigatorio=True),
        'rating': rating,
    }