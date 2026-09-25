import unittest

from app import app


class PortfolioApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_cria_profile_e_busca_por_id(self):
        response = self.client.post('/api/profiles', json={
            'name': 'Ada Lovelace',
            'bio': 'Desenvolvedora Python',
            'github_url': 'https://github.com/ada',
        })
        self.assertEqual(response.status_code, 201)
        profile_id = response.get_json()['id']

        response = self.client.get(f'/api/profiles/{profile_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['name'], 'Ada Lovelace')

    def test_valida_profile_e_technology(self):
        response = self.client.post('/api/profiles', json={'name': ''})
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/technologies', json={
            'name': 'Python',
            'icon_url': 'endereco-invalido',
        })
        self.assertEqual(response.status_code, 400)

    def test_cria_project_com_tecnologias_e_lista(self):
        profile = self.client.post('/api/profiles', json={'name': 'Grace Hopper'}).get_json()
        technology = self.client.post('/api/technologies', json={'name': 'Flask-Api-Test'}).get_json()

        response = self.client.post('/api/projects', json={
            'profile_id': profile['id'],
            'title': 'Portfolio API',
            'description': 'API de portfólio',
            'repository_url': 'https://github.com/grace/portfolio',
            'technology_ids': [technology['id']],
        })
        self.assertEqual(response.status_code, 201)
        project = response.get_json()
        self.assertEqual(project['technologies'][0]['name'], 'Flask-Api-Test')
        self.assertEqual(project['feedbacks'], [])

        response = self.client.post(f"/api/projects/{project['id']}/feedback", json={
            'author_name': 'Cliente',
            'content': 'Excelente projeto',
            'rating': 5,
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/api/projects')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['id'] == project['id'] for item in response.get_json()))


if __name__ == '__main__':
    unittest.main()