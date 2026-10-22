"""Propriedades dos conjuntos sintéticos e das cópias ordenadas."""

from datetime import date
import random
import unittest

from gerar_dados import embaralhar_pacientes, gerar_pacientes, ordenar_pacientes


class TestGerarDados(unittest.TestCase):
    def test_quantidade_unicidade_e_validade(self):
        for quantidade in (0, 7, 100, 1_000, 10_000):
            with self.subTest(quantidade=quantidade):
                pacientes = gerar_pacientes(quantidade)
                self.assertEqual(len(pacientes), quantidade)
                self.assertEqual(len({p.prontuario for p in pacientes}), quantidade)
                for paciente in pacientes:
                    date.fromisoformat(paciente.data_nascimento)
                    self.assertTrue(paciente.telefone.startswith("00"))
                    self.assertEqual(len(paciente.telefone), 11)

    def test_reprodutibilidade(self):
        self.assertEqual(gerar_pacientes(20, seed=42), gerar_pacientes(20, seed=42))
        self.assertNotEqual(gerar_pacientes(20, seed=42), gerar_pacientes(20, seed=43))

    def test_ordenacao_e_embaralhamento_nao_alteram_original(self):
        pacientes = gerar_pacientes(30)
        original = pacientes.copy()
        aleatorios = embaralhar_pacientes(pacientes, seed=7)
        self.assertEqual(aleatorios, embaralhar_pacientes(pacientes, seed=7))
        self.assertNotEqual(aleatorios, pacientes)
        self.assertEqual(ordenar_pacientes(aleatorios), pacientes)
        self.assertEqual(pacientes, original)
        self.assertIsNot(ordenar_pacientes(pacientes), pacientes)
        self.assertIsNot(aleatorios, pacientes)

    def test_preserva_estado_aleatorio_global(self):
        estado = random.getstate()
        gerar_pacientes(10)
        embaralhar_pacientes(gerar_pacientes(10))
        self.assertEqual(random.getstate(), estado)

    def test_prontuario_inicial(self):
        self.assertEqual([p.prontuario for p in gerar_pacientes(3, prontuario_inicial=8)],
                         [8, 9, 10])

    def test_argumentos_invalidos(self):
        for quantidade in (-1,):
            with self.assertRaises(ValueError):
                gerar_pacientes(quantidade)
        for quantidade in (True, 1.2, "10"):
            with self.assertRaises(TypeError):
                gerar_pacientes(quantidade)
        for inicial in (0, -1):
            with self.assertRaises(ValueError):
                gerar_pacientes(1, prontuario_inicial=inicial)
        with self.assertRaises(TypeError):
            gerar_pacientes(1, prontuario_inicial=True)


if __name__ == "__main__":
    unittest.main()
