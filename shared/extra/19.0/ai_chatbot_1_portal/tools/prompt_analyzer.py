#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador de prompts de clientes para bots de atencion.

Extrae las reglas (REGLA <nombre>) de un prompt, mide la longitud de sus
respuestas y las compara contra los limites de caracteres por plataforma.
Tambien valida estructura del JSON de salida, consistencia del menu, CTA,
y detecta keywords ambiguos entre reglas.

Uso:
    python3 prompt_analyzer.py prompt.txt
    cat prompt.txt | python3 prompt_analyzer.py
    python3 prompt_analyzer.py prompt.txt --json

Salida legible en consola o JSON estructurado con --json.
"""

import argparse
import json
import re
import sys
from collections import Counter

# Limites de caracteres por plataforma (coinciden con la regla 1A del prompt)
PLATFORM_LIMITS = {
    'instagram': 900,
    'messenger': 900,
    'facebook': 900,
    'meta': 900,
    'whatsapp': 4000,
    '': 1000,
}

OTHER_LIMIT = 4000  # plataformas no listadas (telegram, web, etc.)

REQUIRED_JSON_KEYS = [
    'output', 'tipoPregunta', 'isMenu', 'equipo_asignado', 'flow_name',
    'session_id', 'conversation_id', 'account_id', 'platform',
    'timestamp_actividad',
]

ALLOWED_TIPO_PREGUNTA = [
    'PRECIOS', 'SERVICIOS', 'CITA_DIRECTA', 'TARJETA', 'OTRA_CONSULTA',
    'ESTATICO', 'RESULTADOS', 'CONFIRMACION', '',
]

ALLOWED_EQUIPO = [
    '', 'Agendamiento_Directo', 'Ventas_UNISA', 'CITAS_MP', 'CITAS_SEGUROS',
    'RESULTADOS_LAB', 'RESULTADOS_IMAGENES',
]

MENU_OPTIONS = {  # opcion del menu maestro -> tipoPregunta esperado
    '1': 'PRECIOS', '2': 'SERVICIOS', '3': 'CITA_DIRECTA',
    '4': 'TARJETA', '5': 'OTRA_CONSULTA',
}

CTA_PATTERNS = [
    r'agend', r'cita', r'contact',
    r'cotiz', r'¿qu', r'as.?esor', r'llamad', r'demo',
]

# Use: seccion -> patron que extrae los keywords de esa seccion
KEYWORD_SECTIONS = {
    '4.1 PRECIOS': r'4\.1\s+PRECIOS[^\n]*menciona[:]?\s*(.*)',
    '4.2 SERVICIOS': r'4\.2\s+SERVICIOS[^\n]*menciona[:]?\s*(.*)',
    '4.3 CITA_DIRECTA': r'4\.3\s+CITA_DIRECTA[^\n]*menciona[:]?\s*(.*)',
    '4.4 TARJETA': r'4\.4\s+TARJETA[^\n]*menciona[:]?\s*(.*)',
    '4.5 OTRA_CONSULTA': r'4\.5\s+OTRA_CONSULTA[^\n]*menciona[:]?\s*(.*)',
    '4.6 CONTACTO': r'4\.6\s+CONTACTO[^\n]*menciona[:]?\s*(.*)',
    '4.7 PROMOCIONES': r'4\.7\s+PROMOCIONES[^\n]*menciona[:]?\s*(.*)',
    '4.8 RESULTADOS': r'4\.8\s+RESULTADOS[^\n]*menciona[:]?\s*(.*)',
}

REQUISITOS_META_ANCHOR = 'PRIORIDAD 3B'


class PromptAnalyzer:
    """Analiza un prompt de bot: reglas, longitudes, JSON y consistencia."""

    def __init__(self, text):
        self.text = text
        self.rules = []          # list[dict]
        self.issues = []         # list[dict] {tipo, severidad, mensaje, regla}
        self.meta_keywords = {}  # seccion -> list[keyword]

    # ------------------------------------------------------------------
    #  PARSING
    # ------------------------------------------------------------------
    def analyze(self):
        self._parse_rules()
        self._check_lengths()
        self._check_json_structure()
        self._check_menu_consistency()
        self._check_cta()
        self._check_keywords()
        return self.rules

    def _parse_rules(self):
        # Divide el prompt por cada cabecera "REGLA <nombre>:"
        segments = re.split(r'(?m)^\s*REGLA\s+([A-Z0-9_]+)\s*:\s*', self.text)
        # segments[0] es el preámbulo; luego alternan nombre, cuerpo
        for idx in range(1, len(segments), 2):
            name = segments[idx]
            body = segments[idx + 1] if idx + 1 < len(segments) else ''
            rule = self._parse_rule(name, body)
            self.rules.append(rule)

    def _parse_rule(self, name, body):
        rule = {
            'name': name,
            'tipoPregunta': '',
            'isMenu': False,
            'equipo_asignado': '',
            'output': '',
            'output_main': '',
            'short_version': '',
            'has_output_block': False,
            'note': '',
        }

        # Metadatos de la cabecera: (tipoPregunta "X", isMenu true, equipo "Y")
        head_meta = re.search(
            r'\(tipoPregunta\s+"([^"]*)"\s*,\s*isMenu\s+(true|false)\s*,'
            r'\s*equipo\s+"([^"]*)"\)', body)
        if head_meta:
            rule['tipoPregunta'] = head_meta.group(1)
            rule['isMenu'] = head_meta.group(2) == 'true'
            rule['equipo_asignado'] = head_meta.group(3)

        # Metadatos en linea: output: "...", tipoPregunta: "...", ...
        inline_meta = re.search(
            r'output\s*:\s*"[^"]*"\s*,\s*tipoPregunta\s*:\s*"([^"]*)"\s*,'
            r'\s*isMenu\s*:\s*(true|false)\s*,'
            r'\s*equipo_asignado\s*:\s*"([^"]*)"', body)
        if inline_meta:
            rule['tipoPregunta'] = inline_meta.group(1)
            rule['isMenu'] = inline_meta.group(2) == 'true'
            rule['equipo_asignado'] = inline_meta.group(3)
            # output inline vacio: output: ""
            m_out = re.search(r'output\s*:\s*"([^"]*)"', body)
            if m_out:
                rule['output'] = m_out.group(1)
                rule['has_output_block'] = True
                return rule

        # Bloque multi-linea: "output:" seguido del texto hasta la siguiente
        # seccion (otra REGLA, linea ====, CONSTRUCCION FINAL, EJEMPLOS)
        m = re.search(r'(?m)^\s*output\s*:\s*\n?', body)
        if m:
            start = m.end()
            end_block = re.search(
                r'(?m)^\s*(?:REGLA\s+[A-Z0-9_]+|'
                r'={2,}|CONSTRUCCION FINAL|EJEMPLOS DE SALIDA)', body[start:])
            end = body.find(end_block.group(0)) if end_block else len(body)
            block = body[start:end]
            # Nota antes del output (ej. "Esta regla se aplica si...")
            pre = body[:m.start()]
            if pre.strip():
                rule['note'] = ' '.join(line.strip() for line in pre.splitlines() if line.strip())
            # Quitar linea de metadatos posterior: tipoPregunta: "...". isMenu...
            block = re.sub(
                r'\s*tipoPregunta\s*:\s*"[^"]*"\s*\.\s*isMenu\s*:\s*(true|false)'
                r'\s*\.\s*equipo_asignado\s*:\s*"[^"]*"\s*\.?\s*$', '', block)
            block = block.strip('\n\r\t ')
            rule['output_main'] = block
            # Separar version corta obligatoria embebida
            short_m = re.search(
                r'(?m)^VERSIÓN CORTA OBLIGATORIA[^\n]*\n(.*?)(?=^REGLA\s|\Z)',
                block, re.DOTALL)
            if short_m:
                rule['short_version'] = short_m.group(1).strip()
                rule['output'] = block[:short_m.start()].strip()
            else:
                rule['output'] = block
            rule['has_output_block'] = True
        return rule

    # ------------------------------------------------------------------
    #  VALIDACIONES
    # ------------------------------------------------------------------
    def _limits(self):
        limits = {}
        for rule in self.rules:
            limits[rule['name']] = {
                platform: self._limit_for(platform)
                for platform in list(PLATFORM_LIMITS) + ['instagram', 'whatsapp']
            }
        return limits

    def _limit_for(self, platform):
        return PLATFORM_LIMITS.get(platform, OTHER_LIMIT)

    def _check_lengths(self):
        for rule in self.rules:
            if not rule['has_output_block'] and not rule['output']:
                continue
            length = len(rule['output'])
            has_short = bool(rule.get('short_version'))
            for platform, limit in PLATFORM_LIMITS.items():
                meta_platform = platform in ('instagram', 'messenger', 'facebook', 'meta')
                effective_limit = limit if not (meta_platform and has_short) else len(rule['short_version'])
                if has_short and meta_platform:
                    # la version corta reemplaza al output en plataformas Meta
                    if effective_limit > 900:
                        self.issues.append({
                            'tipo': 'LONGITUD',
                            'severidad': 'CRITICO',
                            'regla': rule['name'],
                            'plataforma': platform,
                            'mensaje': (
                                f"version corta de {effective_limit} chars "
                                f"excede el limite de 900 para {platform}."
                            ),
                        })
                    continue
                if length > limit:
                    self.issues.append({
                        'tipo': 'LONGITUD',
                        'severidad': 'CRITICO' if length > OTHER_LIMIT else 'ADVERTENCIA',
                        'regla': rule['name'],
                        'plataforma': platform or '(vacio)',
                        'mensaje': (
                            f"output de {length} chars excede el limite de "
                            f"{limit} para {platform or '(vacio)'}."
                            + ('' if has_short else '  (regla sin version corta para Meta)')
                        ),
                    })

    def _check_json_structure(self):
        # Claves obligatorias mencionadas en el prompt
        for key in REQUIRED_JSON_KEYS:
            if not re.search(r'\b%s\b' % re.escape(key), self.text):
                self.issues.append({
                    'tipo': 'JSON',
                    'severidad': 'CRITICO',
                    'regla': 'GLOBAL',
                    'mensaje': f"La clave '{key}' no esta definida en el prompt.",
                })
        # tipoPregunta usados en reglas vs valores permitidos
        used = Counter(r['tipoPregunta'] for r in self.rules)
        for value, count in used.items():
            if value not in ALLOWED_TIPO_PREGUNTA:
                self.issues.append({
                    'tipo': 'JSON',
                    'severidad': 'CRITICO',
                    'regla': 'GLOBAL',
                    'mensaje': (
                        f"tipoPregunta '{value}' usado {count}x no esta en "
                        f"la lista permitida: {ALLOWED_TIPO_PREGUNTA}."
                    ),
                })
        # equipo_asignado usados vs valores permitidos
        used_equipo = Counter(r['equipo_asignado'] for r in self.rules)
        for value, count in used_equipo.items():
            if value not in ALLOWED_EQUIPO:
                self.issues.append({
                    'tipo': 'JSON',
                    'severidad': 'ADVERTENCIA',
                    'regla': 'GLOBAL',
                    'mensaje': (
                        f"equipo_asignado '{value}' usado {count}x no esta en "
                        f"la lista permitida: {ALLOWED_EQUIPO}."
                    ),
                })

    def _check_menu_consistency(self):
        for option, expected in MENU_OPTIONS.items():
            # Buscar en la seccion del menu maestro la correspondencia
            if not self._has_rule_for(expected):
                self.issues.append({
                    'tipo': 'MENU',
                    'severidad': 'ADVERTENCIA',
                    'regla': 'GLOBAL',
                    'mensaje': (
                        f"La opcion {option} del menu espera tipoPregunta "
                        f"'{expected}' pero no hay REGLA que la cubra."
                    ),
                })

    def _has_rule_for(self, tipo):
        return any(r['tipoPregunta'] == tipo for r in self.rules)

    def _check_cta(self):
        for rule in self.rules:
            if not rule['output']:
                continue
            out_lower = rule['output'].lower()
            if not self._has_cta(out_lower):
                self.issues.append({
                    'tipo': 'CTA',
                    'severidad': 'ADVERTENCIA',
                    'regla': rule['name'],
                    'mensaje': (
                        "El output no invita a un siguiente paso "
                        "(falta CTA de cita o contacto)."
                    ),
                })

    def _has_cta(self, text):
        return any(re.search(p, text) for p in CTA_PATTERNS)

    def _extract_keywords(self):
        if self.meta_keywords:
            return self.meta_keywords
        for label, pattern in KEYWORD_SECTIONS.items():
            m = re.search(pattern, self.text, re.IGNORECASE)
            if m:
                keywords = re.findall(r'"([^"]+)"', m.group(1) or '')
                self.meta_keywords[label] = [k.lower() for k in keywords]
        # REQUISITOS_META: bullets entre el anchor y la siguiente seccion
        anchor_m = re.search(self._regex_anchor(REQUISITOS_META_ANCHOR), self.text)
        if anchor_m:
            seg = self.text[anchor_m.end():]
            next_sec = re.search(r'(?m)^\s*PRIORIDAD\s+\d', seg)
            seg = seg[:next_sec.start()] if next_sec else seg
            bullets = re.findall(r'(?m)^\s*-\s*([^\n]+)', seg)
            self.meta_keywords['REQUISITOS_META'] = [b.strip().lower() for b in bullets]
        return self.meta_keywords

    def _regex_anchor(self, anchor):
        return r'(?m)^\s*' + re.escape(anchor)

    def _check_keywords(self):
        kw = self._extract_keywords()
        # Map keyword -> secciones donde aparece
        appear = {}
        for section, words in kw.items():
            for word in words:
                if not word or len(word) < 3:
                    continue
                appear.setdefault(word, set()).add(section)
        for word, sections in appear.items():
            if len(sections) > 1:
                self.issues.append({
                    'tipo': 'AMBIGUEDAD',
                    'severidad': 'ADVERTENCIA',
                    'regla': 'GLOBAL',
                    'mensaje': (
                        f"Keyword '{word}' aparece en multiples secciones: "
                        f"{', '.join(sorted(sections))}."
                    ),
                })

    # ------------------------------------------------------------------
    #  REPORTE
    # ------------------------------------------------------------------
    def issues_by_type(self, tipo):
        return [i for i in self.issues if i['tipo'] == tipo]

    def generate_report(self):
        lines = []
        lines.append('=' * 70)
        lines.append(f'ANALISIS DE PROMPT: {len(self.rules)} reglas detectadas')
        lines.append('=' * 70)
        lines.append('')
        lines.append('--- LONGITUDES DE OUTPUT POR REGLA ---')
        header = (f"{'REGLA':<24}{'chars':>7}{'IG/Meta(900)':>16}"
                  f"{'WhatsApp(4000)':>16}{'Estado':>16}")
        lines.append(header)
        lines.append('-' * len(header))
        for rule in sorted(self.rules, key=lambda r: -len(r['output_main'])):
            if not rule['has_output_block'] and not rule['output']:
                continue
            length = len(rule['output_main'])
            has_short = bool(rule.get('short_version'))
            ig = PLATFORM_LIMITS['instagram']
            wa = PLATFORM_LIMITS['whatsapp']
            if has_short:
                status = f"OK corta={len(rule['short_version']) }"
                if len(rule['short_version']) > 900:
                    status = 'CORTA LARGA!'
            elif length > wa:
                status = 'SOBREPASA TODO'
            elif length > ig:
                status = 'Excede 900 (sin corta)'
            else:
                status = 'OK'
            lines.append(f"{rule['name']:<24}{len(rule['output_main']):>7}"
                         f"{' ' if has_short or length <= ig else ' X':>16}"
                         f"{' ' if length <= wa else ' X':>16}{status:>16}")
        lines.append('')
        lines.append('--- TIPO PREGUNTA DE CADA REGLA ---')
        for rule in self.rules:
            estado = 'OK' if rule['tipoPregunta'] in ALLOWED_TIPO_PREGUNTA else 'INVALIDO'
            menu = 'menu' if rule['isMenu'] else '    '
            lines.append(
                f"  {rule['name']:<24} tipoPregunta={rule['tipoPregunta'] or '""':<16}"
                f" isMenu={rule['isMenu']} equipo={rule['equipo_asignado'] or '""':<22} {estado} {menu}"
            )
        lines.append('')

        lines.append('--- ISSUES DETECTADOS ---')
        if not self.issues:
            lines.append('  No se detectaron problemas. ✓')
        for issue in self.issues:
            sev = {'CRITICO': 'X', 'ADVERTENCIA': '!'}.get(issue['severidad'], '?')
            extra = ''
            if 'plataforma' in issue:
                extra = f" [{issue['plataforma']}]"
            lines.append(f"  [{sev}] {issue['tipo']}{extra} "
                         f"(regla {issue['regla']}): {issue['mensaje']}")
        lines.append('')
        lines.append('--- CONSEJOS PARA INSTAGRAM (auto-resumen sugerido) ---')
        for rule in sorted(self.rules, key=lambda r: -len(r['output_main'])):
            length = len(rule['output_main'])
            if length > PLATFORM_LIMITS['instagram'] and rule['output']:
                if rule.get('short_version'):
                    lines.append(
                        f"  * {rule['name']} (main={length}) ya tiene version corta "
                        f"de {len(rule['short_version'])} chars -> OK."
                    )
                else:
                    lines.append(
                        f"  * {rule['name']} (main={length} chars): recorta a <=900. "
                        f"Conserva precios USD y CTA de cita."
                    )
        return '\n'.join(lines)

    def to_json(self):
        return json.dumps({
            'total_rules': len(self.rules),
            'rules': [
                {
                    'name': r['name'],
                    'tipoPregunta': r['tipoPregunta'],
                    'isMenu': r['isMenu'],
                    'equipo_asignado': r['equipo_asignado'],
                    'output_chars': len(r['output']),
                    'output_main_chars': len(r['output_main']),
                    'short_version_chars': len(r.get('short_version') or ''),
                    'has_short_version': bool(r.get('short_version')),
                    'output': r['output'],
                } for r in self.rules
            ],
            'issues': self.issues,
        }, ensure_ascii=False, indent=2)


def read_input(args):
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            return f.read()
    return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(
        description='Analiza prompts de bots (límites por plataforma + JSON).')
    parser.add_argument('file', nargs='?', help='Archivo con el prompt (si no, stdin)')
    parser.add_argument('--json', action='store_true', help='Salida JSON estructurada')
    args = parser.parse_args()

    text = read_input(args)
    if not text.strip():
        print('ERROR: no se recibio contenido de prompt.', file=sys.stderr)
        sys.exit(2)

    analyzer = PromptAnalyzer(text)
    analyzer.analyze()
    if args.json:
        print(analyzer.to_json())
    else:
        print(analyzer.generate_report())


if __name__ == '__main__':
    main()