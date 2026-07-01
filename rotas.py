from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, Response
from database import listar_clientes, adicionar_cliente, listar_ordens, adicionar_ordem, buscar_cliente_por_id, buscar_ordem_por_id, buscar_itens_ordem, atualizar_ordem, excluir_ordem, get_servicos
from ia_modulo import analisar_risco


def calcular_resumo_financeiro(ordens):
    hoje = datetime.now().strftime('%Y-%m')
    ordens_mes = [
        ordem for ordem in ordens
        if ordem['status'] == 'Concluído' and str(ordem['data_abertura']).startswith(hoje)
    ]
    faturamento = sum(float(ordem['valor_total']) for ordem in ordens_mes)
    lucro_bruto_mensal = sum(float(ordem['valor_mao_de_obra']) for ordem in ordens_mes)
    lucro_bruto_anual = lucro_bruto_mensal * 12
    return {
        'faturamento': faturamento,
        'lucro_bruto_mensal': lucro_bruto_mensal,
        'lucro_bruto_anual': lucro_bruto_anual,
    }


def gerar_pdf_ordem(ordem, cliente, itens):
    linhas = [
        'TECOS - Ordem de Servico',
        '========================',
        'Documento profissional de servico',
        '',
        f'ID: {ordem["id"]}',
        f'Cliente: {cliente["nome"] if cliente else "Não informado"}',
        f'Tipo: {ordem["tipo_servico"]}',
        f'Status: {ordem["status"]}',
        f'Data: {ordem["data_abertura"]}',
        '',
        'Descricao do problema:',
        ordem['descricao_problema'],
        '',
        'Resumo financeiro:',
        f'Valor Material: R$ {ordem["valor_material"]:.2f}',
        f'Valor Mao de Obra: R$ {ordem["valor_mao_de_obra"]:.2f}',
        f'Valor Total: R$ {ordem["valor_total"]:.2f}',
        '',
        'Itens:',
    ]
    for item in itens:
        linhas.append(f'- {item["servico"]} | qtd {item["quantidade"]} | R$ {item["valor_total"]:.2f}')
    linhas.extend(['', 'Assinatura do tecnico:', '__________________________'])
    body = '\n'.join(linhas).encode('latin-1', 'replace')
    return Response(body, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=ordem_{ordem["id"]}.pdf'})


def gerar_pdf_nota_fiscal(ordem, cliente, itens):
    linhas = [
        'TECOS - Nota Fiscal',
        '===================',
        'Documento simplificado',
        '',
        f'Numero: NF-{ordem["id"]:04d}',
        f'Cliente: {cliente["nome"] if cliente else "Não informado"}',
        f'Data: {ordem["data_abertura"]}',
        '',
        'Servicos:',
    ]
    for item in itens:
        linhas.append(f'- {item["servico"]} | qtd {item["quantidade"]} | R$ {item["valor_total"]:.2f}')
    linhas.extend([
        '',
        f'Valor Material: R$ {ordem["valor_material"]:.2f}',
        f'Valor Mao de Obra: R$ {ordem["valor_mao_de_obra"]:.2f}',
        f'Valor Total: R$ {ordem["valor_total"]:.2f}',
        '',
        'Obrigado por contratar os servicos!',
    ])
    body = '\n'.join(linhas).encode('latin-1', 'replace')
    return Response(body, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=nota_{ordem["id"]}.pdf'})


def register_routes(app):
    @app.route('/')
    def index():
        status_filter = request.args.get('status')
        if status_filter == 'Pendente':
            ordens = listar_ordens(status='Pendente', limit=8)
        elif status_filter == 'Concluído':
            ordens = listar_ordens(status='Concluído', limit=8)
        else:
            ordens = listar_ordens(limit=8)
        pendentes = sum(1 for ordem in listar_ordens(status='Pendente'))
        todas_ordens = listar_ordens()
        resumo = calcular_resumo_financeiro(todas_ordens)
        status_counts = {}
        for ordem in todas_ordens:
            status_counts[ordem['status']] = status_counts.get(ordem['status'], 0) + 1
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        valores_mensais = [0] * 12
        lucros_mensais = [0] * 12
        for ordem in todas_ordens:
            if str(ordem['data_abertura']).count('-') == 2:
                try:
                    mes = int(str(ordem['data_abertura'])[5:7]) - 1
                    valores_mensais[mes] += float(ordem['valor_total'])
                    lucros_mensais[mes] += float(ordem['valor_mao_de_obra'])
                except ValueError:
                    pass
        return render_template(
            'index.html',
            ordens=ordens,
            pendentes=pendentes,
            faturamento=resumo['faturamento'],
            lucro_bruto_mensal=resumo['lucro_bruto_mensal'],
            lucro_bruto_anual=resumo['lucro_bruto_anual'],
            meses=meses,
            valores_mensais=valores_mensais,
            lucros_mensais=lucros_mensais,
            status_counts=status_counts,
        )

    @app.route('/clientes', methods=['GET', 'POST'])
    def clientes():
        if request.method == 'POST':
            nome = request.form['nome']
            telefone = request.form['telefone']
            endereco = request.form['endereco']
            adicionar_cliente(nome, telefone, endereco)
            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        clientes_cadastrados = listar_clientes()
        return render_template('clientes.html', clientes=clientes_cadastrados)

    @app.route('/nova-os', methods=['GET', 'POST'])
    def nova_os():
        if request.method == 'POST':
            cliente_id = request.form['cliente_id']
            descricao_problema = request.form['descricao_problema']
            tipo_servico = request.form['tipo_servico']
            valor_material = request.form['valor_material']
            valor_mao_de_obra_manual = request.form.get('valor_mao_de_obra_manual', '').strip()
            status = request.form['status']
            data_abertura = datetime.now().strftime('%Y-%m-%d')

            servicos_request = request.form.getlist('servico')
            quantidades_request = request.form.getlist('quantidade')
            servicos = []
            valor_mao_de_obra = 0.0
            servicos_catalogo = get_servicos()
            for servico, quantidade in zip(servicos_request, quantidades_request):
                if not servico:
                    continue
                valor_servico = next((item['valor'] for item in servicos_catalogo if item['nome'] == servico), 0)
                qtd = int(quantidade or 1)
                valor_item = float(valor_servico) * qtd
                valor_mao_de_obra += valor_item
                servicos.append({'nome': servico, 'quantidade': qtd, 'valor': float(valor_servico), 'valor_total': valor_item})

            if valor_mao_de_obra_manual:
                valor_mao_de_obra = float(valor_mao_de_obra_manual)

            adicionar_ordem(cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, status, data_abertura, servicos=servicos)
            flash('Ordem de serviço cadastrada com sucesso!', 'success')
            return redirect(url_for('nova_os'))
        clientes = listar_clientes()
        return render_template('nova_os.html', clientes=clientes, servicos=get_servicos())

    @app.route('/ordem/<int:ordem_id>')
    def detalhe_ordem(ordem_id):
        ordem = buscar_ordem_por_id(ordem_id)
        cliente = buscar_cliente_por_id(ordem['cliente_id']) if ordem else None
        itens = buscar_itens_ordem(ordem_id)
        alerta = analisar_risco(ordem['descricao_problema']) if ordem else None
        return render_template('ordem.html', ordem=ordem, cliente=cliente, itens=itens, alerta=alerta)

    @app.route('/ordem/<int:ordem_id>/pdf')
    def pdf_ordem(ordem_id):
        ordem = buscar_ordem_por_id(ordem_id)
        cliente = buscar_cliente_por_id(ordem['cliente_id']) if ordem else None
        itens = buscar_itens_ordem(ordem_id)
        return gerar_pdf_ordem(ordem, cliente, itens)

    @app.route('/ordem/<int:ordem_id>/nota-fiscal')
    def nota_fiscal(ordem_id):
        ordem = buscar_ordem_por_id(ordem_id)
        cliente = buscar_cliente_por_id(ordem['cliente_id']) if ordem else None
        itens = buscar_itens_ordem(ordem_id)
        return gerar_pdf_nota_fiscal(ordem, cliente, itens)

    @app.route('/ordens-abertas')
    def ordens_abertas():
        cliente_id = request.args.get('cliente_id')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        ordens = listar_ordens(
            status='Pendente',
            cliente_id=int(cliente_id) if cliente_id else None,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        clientes = listar_clientes()
        return render_template(
            'ordens_abertas.html',
            ordens=ordens,
            clientes=clientes,
            cliente_id=cliente_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    @app.route('/relatorio')
    def relatorio():
        cliente_id = request.args.get('cliente_id')
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        ordens = listar_ordens(status=status, cliente_id=int(cliente_id) if cliente_id else None, data_inicio=data_inicio, data_fim=data_fim)
        clientes = listar_clientes()
        return render_template('relatorio.html', ordens=ordens, clientes=clientes, cliente_id=cliente_id, status=status, data_inicio=data_inicio, data_fim=data_fim)

    @app.route('/relatorio/pdf')
    def relatorio_pdf():
        cliente_id = request.args.get('cliente_id')
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        ordens = listar_ordens(status=status, cliente_id=int(cliente_id) if cliente_id else None, data_inicio=data_inicio, data_fim=data_fim)
        linhas = ['Relatorio TecOS', '========================']
        total = sum(ordem['valor_total'] for ordem in ordens)
        for ordem in ordens:
            linhas.append(f'{ordem["id"]} | {ordem["cliente_nome"]} | {ordem["status"]} | R$ {ordem["valor_total"]:.2f}')
        linhas.append(f'TOTAL: R$ {total:.2f}')
        body = '\n'.join(linhas).encode('latin-1', 'replace')
        return Response(body, mimetype='application/pdf', headers={'Content-Disposition': 'attachment; filename=relatorio_tecos.pdf'})

    @app.route('/ordem/<int:ordem_id>/editar', methods=['GET', 'POST'])
    def editar_ordem(ordem_id):
        ordem = buscar_ordem_por_id(ordem_id)
        if request.method == 'POST':
            cliente_id = request.form['cliente_id']
            descricao_problema = request.form['descricao_problema']
            tipo_servico = request.form['tipo_servico']
            valor_material = request.form['valor_material']
            valor_mao_de_obra_manual = request.form.get('valor_mao_de_obra_manual', '').strip()
            status = request.form['status']

            servicos_request = request.form.getlist('servico')
            quantidades_request = request.form.getlist('quantidade')
            servicos = []
            valor_mao_de_obra = 0.0
            servicos_catalogo = get_servicos()
            for servico, quantidade in zip(servicos_request, quantidades_request):
                if not servico:
                    continue
                valor_servico = next((item['valor'] for item in servicos_catalogo if item['nome'] == servico), 0)
                qtd = int(quantidade or 1)
                valor_item = float(valor_servico) * qtd
                valor_mao_de_obra += valor_item
                servicos.append({'nome': servico, 'quantidade': qtd, 'valor': float(valor_servico), 'valor_total': valor_item})

            if valor_mao_de_obra_manual:
                valor_mao_de_obra = float(valor_mao_de_obra_manual)

            atualizar_ordem(ordem_id, cliente_id, descricao_problema, tipo_servico, valor_material, valor_mao_de_obra, status, servicos=servicos)
            flash('Ordem de serviço atualizada com sucesso!', 'success')
            return redirect(url_for('detalhe_ordem', ordem_id=ordem_id))

        clientes = listar_clientes()
        itens = buscar_itens_ordem(ordem_id)
        return render_template('editar_ordem.html', ordem=ordem, clientes=clientes, servicos=get_servicos(), itens=itens)

    @app.route('/ordem/<int:ordem_id>/excluir', methods=['POST'])
    def excluir_ordem_route(ordem_id):
        excluir_ordem(ordem_id)
        flash('Ordem de serviço excluída com sucesso!', 'success')
        return redirect(url_for('index'))
