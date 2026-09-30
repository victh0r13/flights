"""Rastreador de passagens aéreas.

Cada módulo tem uma responsabilidade só:
    config.py        -> quais rotas monitorar (lê e valida config/rotas.json)
    aeroportos.py    -> traduz nome de cidade para código de aeroporto (GRU, LIS...)
    buscador.py      -> consulta os preços no Google Flights
    analise.py       -> calcula menor preço/média e decide se deve avisar
    armazenamento.py -> guarda o histórico de preços e o que já foi avisado
    notificador.py   -> monta e envia o e-mail
"""
