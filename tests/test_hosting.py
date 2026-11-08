"""
Tests de la detección de infraestructura compartida.

Esto decide si Sajjad escanea puertos o no, así que es lógica de
alcance: un falso negativo hace que escaneemos las IPs de un CDN
que el cliente no puede autorizar.
"""

import pytest

from sajjad.analysis.hosting import (
    classify_hosts,
    detect_provider,
    is_shared_infrastructure,
    provider_for_dns,
    provider_for_ip,
)


class TestDeteccionPorDNS:
    """La señal preferente: los CDN rotan IPs, no sus nameservers."""

    @pytest.mark.parametrize(
        "nombres,esperado",
        [
            (["ns1.vercel-dns.com", "ns2.vercel-dns.com"], "Vercel"),
            (["kate.ns.cloudflare.com"], "Cloudflare"),
            (["dns1.p01.nsone.net"], "Netlify"),
            (["cname.shopify.com"], "Shopify"),
            (["d111.cloudfront.net"], "AWS CloudFront"),
            (["ns1.wixdns.net"], "Wix"),
            (["e1234.akamaiedge.net"], "Akamai"),
        ],
    )
    def test_reconoce_proveedores_por_nameserver(self, nombres, esperado):
        assert provider_for_dns(nombres) == esperado

    def test_reconoce_el_destino_de_un_cname(self):
        assert provider_for_dns(["cname.vercel-dns.com"]) == "Vercel"

    def test_no_confunde_un_dominio_propio(self):
        assert provider_for_dns(["ns1.miempresa.com"]) is None

    def test_es_insensible_a_mayusculas(self):
        assert provider_for_dns(["NS1.VERCEL-DNS.COM"]) == "Vercel"

    def test_lista_vacia_no_detecta_nada(self):
        assert provider_for_dns([]) is None


class TestDeteccionPorIP:
    @pytest.mark.parametrize(
        "ip,esperado",
        [
            ("64.29.17.65", "Vercel"),
            ("104.16.0.1", "Cloudflare"),
            ("172.64.1.1", "Cloudflare"),
            ("75.2.60.5", "Netlify"),
            ("185.199.108.153", "GitHub Pages"),
            ("151.101.1.1", "Fastly"),
        ],
    )
    def test_reconoce_rangos_conocidos(self, ip, esperado):
        assert provider_for_ip(ip) == esperado

    def test_ip_propia_no_es_compartida(self):
        # Un VPS típico: esto SÍ debe escanearse.
        assert provider_for_ip("203.0.113.42") is None

    def test_ip_invalida_no_revienta(self):
        assert provider_for_ip("no-es-una-ip") is None
        assert provider_for_ip("") is None


class TestDetectProvider:
    def test_el_dns_tiene_prioridad_sobre_la_ip(self):
        """
        Si el DNS delata al proveedor, no hace falta acertar la IP:
        los rangos publicados envejecen, los nameservers no.
        """
        assert detect_provider(
            ips=["203.0.113.1"],  # fuera de todo rango conocido
            dns_names=["ns1.vercel-dns.com"],
        ) == "Vercel"

    def test_cae_a_la_ip_si_el_dns_no_dice_nada(self):
        assert detect_provider(
            ips=["104.16.0.1"],
            dns_names=["ns1.dnspropio.com"],
        ) == "Cloudflare"

    def test_infraestructura_propia_no_se_omite(self):
        """
        El caso que importa no romper: un cliente con servidor propio
        debe recibir su escaneo de puertos completo.
        """
        assert detect_provider(
            ips=["203.0.113.42"],
            dns_names=["ns1.miempresa.com", "ns2.miempresa.com"],
        ) is None
        assert not is_shared_infrastructure(
            ips=["203.0.113.42"], dns_names=["ns1.miempresa.com"]
        )

    def test_sin_datos_no_asume_nada(self):
        # Sin señales, se escanea: el comportamiento por defecto es
        # el normal, no el de omitir.
        assert detect_provider() is None
        assert detect_provider(ips=[], dns_names=[]) is None

    def test_caso_real_cncentro(self):
        """Regresión del caso que motivó el módulo."""
        assert is_shared_infrastructure(
            ips=["64.29.17.65", "216.198.79.1"],
            dns_names=["ns1.vercel-dns.com", "ns2.vercel-dns.com"],
        )


class TestClasificacionPorHost:
    """
    Lo que de verdad importa: la decisión es por host, no por
    dominio. Que la raíz esté en un CDN no puede hacer que dejemos
    de mirar un servidor propio del cliente.
    """

    def test_separa_hosts_propios_de_los_del_cdn(self):
        registros = [
            {"host": "cncentro.com", "a": ["64.29.17.65"]},
            {"host": "www.cncentro.com",
             "cname": ["cname.vercel-dns.com"]},
            {"host": "erp.cncentro.com", "a": ["203.0.113.10"]},
            {"host": "vpn.cncentro.com", "a": ["203.0.113.11"]},
        ]

        propios, compartidos = classify_hosts(registros)

        # El ERP y la VPN son del cliente: hay que escanearlos.
        assert propios == ["erp.cncentro.com", "vpn.cncentro.com"]
        assert compartidos == {
            "cncentro.com": "Vercel",
            "www.cncentro.com": "Vercel",
        }

    def test_todo_en_cdn_no_deja_hosts_que_escanear(self):
        registros = [
            {"host": "tienda.com", "a": ["64.29.17.65"]},
            {"host": "www.tienda.com", "a": ["104.16.0.1"]},
        ]
        propios, compartidos = classify_hosts(registros)

        assert propios == []
        assert set(compartidos.values()) == {"Vercel", "Cloudflare"}

    def test_infraestructura_propia_se_escanea_entera(self):
        registros = [
            {"host": "empresa.com", "a": ["203.0.113.1"]},
            {"host": "mail.empresa.com", "a": ["203.0.113.2"]},
        ]
        propios, compartidos = classify_hosts(registros)

        assert len(propios) == 2
        assert compartidos == {}

    def test_ignora_registros_sin_host(self):
        propios, compartidos = classify_hosts(
            [{"a": ["203.0.113.1"]}, {"host": "", "a": ["1.2.3.4"]}]
        )
        assert propios == []
        assert compartidos == {}

    def test_host_sin_ip_ni_cname_se_considera_propio(self):
        # Sin señales de CDN, el comportamiento por defecto es
        # escanear: no omitimos por falta de información.
        propios, _ = classify_hosts([{"host": "raro.empresa.com"}])
        assert propios == ["raro.empresa.com"]

    def test_no_duplica_hosts_repetidos(self):
        registros = [
            {"host": "empresa.com", "a": ["203.0.113.1"]},
            {"host": "empresa.com", "a": ["203.0.113.1"]},
        ]
        propios, _ = classify_hosts(registros)
        assert propios == ["empresa.com"]
