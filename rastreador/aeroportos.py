"""Tradução de nome de cidade para código de aeroporto (IATA).

Assim o usuário digita "Lisboa" ou "são paulo" em vez de precisar saber "LIS" ou "GRU".
Códigos fora desta lista também são aceitos se a pessoa digitar as 3 letras.
"""

import unicodedata

# cidade -> [(código, nome do aeroporto)]
CIDADES: dict[str, list[tuple[str, str]]] = {
    # Brasil
    "São Paulo": [("GRU", "Guarulhos"), ("CGH", "Congonhas"), ("VCP", "Viracopos/Campinas")],
    "Rio de Janeiro": [("GIG", "Galeão"), ("SDU", "Santos Dumont")],
    "Brasília": [("BSB", "Brasília")],
    "Belo Horizonte": [("CNF", "Confins"), ("PLU", "Pampulha")],
    "Salvador": [("SSA", "Salvador")],
    "Recife": [("REC", "Recife")],
    "Fortaleza": [("FOR", "Fortaleza")],
    "Porto Alegre": [("POA", "Salgado Filho")],
    "Curitiba": [("CWB", "Afonso Pena")],
    "Florianópolis": [("FLN", "Hercílio Luz")],
    "Manaus": [("MAO", "Eduardo Gomes")],
    "Belém": [("BEL", "Val de Cans")],
    "Natal": [("NAT", "São Gonçalo do Amarante")],
    "Maceió": [("MCZ", "Zumbi dos Palmares")],
    "João Pessoa": [("JPA", "Castro Pinto")],
    "Aracaju": [("AJU", "Santa Maria")],
    "Vitória": [("VIX", "Eurico de Aguiar Salles")],
    "Goiânia": [("GYN", "Santa Genoveva")],
    "Cuiabá": [("CGB", "Marechal Rondon")],
    "Campo Grande": [("CGR", "Campo Grande")],
    "São Luís": [("SLZ", "Marechal Cunha Machado")],
    "Teresina": [("THE", "Teresina")],
    "Porto Seguro": [("BPS", "Porto Seguro")],
    "Foz do Iguaçu": [("IGU", "Cataratas")],
    "Navegantes": [("NVT", "Navegantes")],
    "Joinville": [("JOI", "Joinville")],
    "Londrina": [("LDB", "Londrina")],
    "Uberlândia": [("UDI", "Uberlândia")],
    "Ribeirão Preto": [("RAO", "Leite Lopes")],
    "Porto Velho": [("PVH", "Porto Velho")],
    "Palmas": [("PMW", "Palmas")],
    "Macapá": [("MCP", "Macapá")],
    "Boa Vista": [("BVB", "Boa Vista")],
    "Rio Branco": [("RBR", "Rio Branco")],
    "Fernando de Noronha": [("FEN", "Fernando de Noronha")],
    "Ilhéus": [("IOS", "Jorge Amado")],
    "Chapecó": [("XAP", "Chapecó")],
    # América do Sul e Central
    "Buenos Aires": [("EZE", "Ezeiza"), ("AEP", "Aeroparque")],
    "Santiago": [("SCL", "Santiago do Chile")],
    "Montevidéu": [("MVD", "Carrasco")],
    "Lima": [("LIM", "Jorge Chávez")],
    "Bogotá": [("BOG", "El Dorado")],
    "Cancún": [("CUN", "Cancún")],
    "Cidade do México": [("MEX", "Benito Juárez")],
    "Punta Cana": [("PUJ", "Punta Cana")],
    # América do Norte
    "Miami": [("MIA", "Miami")],
    "Orlando": [("MCO", "Orlando")],
    "Fort Lauderdale": [("FLL", "Fort Lauderdale")],
    "Nova York": [("JFK", "John F. Kennedy"), ("EWR", "Newark"), ("LGA", "LaGuardia")],
    "Los Angeles": [("LAX", "Los Angeles")],
    "Toronto": [("YYZ", "Pearson")],
    # Europa
    "Lisboa": [("LIS", "Humberto Delgado")],
    "Porto": [("OPO", "Francisco Sá Carneiro")],
    "Madri": [("MAD", "Barajas")],
    "Barcelona": [("BCN", "El Prat")],
    "Paris": [("CDG", "Charles de Gaulle"), ("ORY", "Orly")],
    "Londres": [("LHR", "Heathrow"), ("LGW", "Gatwick")],
    "Roma": [("FCO", "Fiumicino")],
    "Milão": [("MXP", "Malpensa")],
    "Amsterdã": [("AMS", "Schiphol")],
    "Frankfurt": [("FRA", "Frankfurt")],
    # Outros
    "Dubai": [("DXB", "Dubai")],
    "Tóquio": [("NRT", "Narita"), ("HND", "Haneda")],
}

def _descrever(cidade: str, aeroporto: str) -> str:
    """'Lisboa (Humberto Delgado)', ou só 'Recife' quando o aeroporto tem o nome da cidade."""
    return cidade if cidade == aeroporto else f"{cidade} ({aeroporto})"


# código -> descrição, para mostrar nomes bonitos
NOMES = {codigo: _descrever(cidade, nome) for cidade, lista in CIDADES.items() for codigo, nome in lista}


def normalizar(texto: str) -> str:
    """'São Paulo ' -> 'sao paulo' (sem acento, minúsculo, sem espaços nas pontas)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def procurar(texto: str) -> list[tuple[str, str]]:
    """Devolve os aeroportos que combinam com o texto digitado: [(código, descrição)].

    Ordem de tentativa: código conhecido -> cidade exata -> cidade que contém o texto
    -> se nada combinar e forem 3 letras, aceita como código (fora da lista).
    """
    busca = normalizar(texto)
    if not busca:
        return []

    if busca.upper() in NOMES:
        return [(busca.upper(), NOMES[busca.upper()])]

    exatas = [c for c in CIDADES if normalizar(c) == busca]
    parecidas = exatas or [c for c in CIDADES if busca in normalizar(c)]
    if parecidas:
        return [(codigo, _descrever(cidade, nome)) for cidade in parecidas for codigo, nome in CIDADES[cidade]]

    if len(busca) == 3 and busca.isalpha():
        return [(busca.upper(), "código fora da lista — confira se está certo")]
    return []


def nome(codigo: str) -> str:
    return NOMES.get(codigo, codigo)
