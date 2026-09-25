def analisar_risco(descricao):
    texto = descricao.lower()
    palavras_chave = ['trifásico', 'alta tensão', 'quadro geral', 'padrão']
    if any(palavra in texto for palavra in palavras_chave):
        return (
            '[IA Alerta]: Este serviço envolve circuitos de alta potência. '
            'Obrigatório o uso de EPIs específicos (Luvas de isolamento classe X, '
            'óculos de proteção) e desenergização do circuito principal.'
        )
    return 'Nenhum alerta identificado.'
