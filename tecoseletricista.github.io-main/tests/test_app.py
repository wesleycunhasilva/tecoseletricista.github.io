import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import get_connection, adicionar_cliente
from rotas import calcular_resumo_financeiro


class TecOSAppTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_dashboard_page_loads(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_clientes_page_loads(self):
        response = self.app.get('/clientes')
        self.assertEqual(response.status_code, 200)

    def test_nova_os_page_loads(self):
        response = self.app.get('/nova-os')
        self.assertEqual(response.status_code, 200)

    def test_calcula_mao_de_obra_from_service(self):
        adicionar_cliente('Maria', '11999999999', 'Rua A')
        response = self.app.post('/nova-os', data={
            'cliente_id': '1',
            'descricao_problema': 'Problema de tomada',
            'tipo_servico': 'Residencial',
            'valor_material': '20',
            'servico': 'Tomada',
            'quantidade': '2',
            'status': 'Pendente'
        })

        self.assertEqual(response.status_code, 302)
        conn = get_connection()
        ordem = conn.execute('SELECT valor_mao_de_obra, valor_total FROM ordens_servico ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        self.assertEqual(ordem['valor_mao_de_obra'], 70.0)
        self.assertEqual(ordem['valor_total'], 90.0)

    def test_cria_ordem_com_varios_servicos(self):
        adicionar_cliente('Joao', '11888888888', 'Rua B')
        response = self.app.post('/nova-os', data={
            'cliente_id': '2',
            'descricao_problema': 'Problema no quadro',
            'tipo_servico': 'Comercial',
            'valor_material': '50',
            'servico': ['Tomada', 'Quebrar'],
            'quantidade': ['2', '1'],
            'status': 'Em Andamento'
        })

        self.assertEqual(response.status_code, 302)
        conn = get_connection()
        ordem = conn.execute('SELECT id, valor_mao_de_obra, valor_total FROM ordens_servico ORDER BY id DESC LIMIT 1').fetchone()
        itens = conn.execute('SELECT COUNT(*) as total FROM ordem_servico_itens WHERE ordem_id = ?', (ordem['id'],)).fetchone()
        conn.close()
        self.assertEqual(itens['total'], 2)
        self.assertEqual(ordem['valor_mao_de_obra'], 85.0)
        self.assertEqual(ordem['valor_total'], 135.0)

    def test_edita_e_exclui_ordem(self):
        adicionar_cliente('Ana', '11777777777', 'Rua C')
        self.app.post('/nova-os', data={
            'cliente_id': '3',
            'descricao_problema': 'Falha inicial',
            'tipo_servico': 'Residencial',
            'valor_material': '10',
            'servico': 'Quebrar',
            'quantidade': '1',
            'status': 'Pendente'
        })
        conn = get_connection()
        ordem = conn.execute('SELECT id FROM ordens_servico ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()

        edit_response = self.app.post(f'/ordem/{ordem["id"]}/editar', data={
            'cliente_id': '3',
            'descricao_problema': 'Falha corrigida',
            'tipo_servico': 'Industrial',
            'valor_material': '15',
            'status': 'Concluído',
            'servico': ['Tomada'],
            'quantidade': ['1']
        })
        self.assertEqual(edit_response.status_code, 302)

        delete_response = self.app.post(f'/ordem/{ordem["id"]}/excluir')
        self.assertEqual(delete_response.status_code, 302)

    def test_gera_pdf_da_ordem(self):
        adicionar_cliente('Pedro', '11666666666', 'Rua D')
        self.app.post('/nova-os', data={
            'cliente_id': '4',
            'descricao_problema': 'Quadro com falha',
            'tipo_servico': 'Industrial',
            'valor_material': '100',
            'servico': 'Quadro de Distribuição',
            'quantidade': '1',
            'status': 'Pendente'
        })
        conn = get_connection()
        ordem = conn.execute('SELECT id FROM ordens_servico ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()

        response = self.app.get(f'/ordem/{ordem["id"]}/pdf')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.content_type)

    def test_exporta_relatorio_em_pdf(self):
        response = self.app.get('/relatorio/pdf?data_inicio=2024-01-01&data_fim=2030-12-31')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.content_type)

    def test_gera_nota_fiscal_em_pdf(self):
        conn = get_connection()
        ordem = conn.execute('SELECT id FROM ordens_servico ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        response = self.app.get(f'/ordem/{ordem["id"]}/nota-fiscal')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.content_type)

    def test_calcula_resumo_financeiro_do_mes_atual(self):
        from datetime import datetime
        mes_atual = datetime.now().strftime('%Y-%m')
        ordem_mes_atual = {'status': 'Concluído', 'data_abertura': f'{mes_atual}-10', 'valor_total': 200.0, 'valor_mao_de_obra': 80.0}
        ordem_mes_anterior = {'status': 'Concluído', 'data_abertura': '2024-01-10', 'valor_total': 999.0, 'valor_mao_de_obra': 999.0}

        resumo = calcular_resumo_financeiro([ordem_mes_atual, ordem_mes_anterior])

        self.assertEqual(resumo['faturamento'], 200.0)
        self.assertEqual(resumo['lucro_bruto_mensal'], 80.0)
        self.assertEqual(resumo['lucro_bruto_anual'], 960.0)


if __name__ == '__main__':
    unittest.main()
