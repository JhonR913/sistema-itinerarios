#!/usr/bin/env python3
"""Prueba visual del flujo de agenda con un navegador real (Playwright/Chromium).
Requiere el sistema levantado (docker compose up) y Playwright: pip install playwright && playwright install chromium.
URL de la app: UI_URL (def. http://localhost, el Traefik de Compose); capturas: UI_SHOTS_DIR. Crea un viajero nuevo en cada corrida. No esta integrada al CI."""
import os, re, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
BOG=timezone(timedelta(hours=-5))
day=(datetime.now(BOG)+timedelta(days=15)).strftime("%Y-%m-%d")
# Capturas en una carpeta del proyecto (no en /tmp, que es de escritura publica).
SHOTS = Path(os.environ.get("UI_SHOTS_DIR", Path(__file__).resolve().parent.parent / "docs" / "evidencias" / "capturas"))
SHOTS.mkdir(parents=True, exist_ok=True)
UI_URL = os.environ.get("UI_URL", "http://localhost")


def log(ok,msg): print(("[OK] " if ok else "[FALLA] ")+msg, flush=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1400,"height":950})
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e))); pg.on("console",lambda m: errs.append(m.text) if m.type=="error" and not re.search(r"status of 40[01]", m.text) else None)  # 400/401 esperados: codigo/contrasena incorrectos y /refresh sin sesion
    pg.goto(UI_URL); pg.wait_for_selector("#login-username")
    import json, urllib.request, uuid
    MAILPIT = os.environ.get("MAILPIT_URL", "http://localhost:8025")
    email = f"viajero-{uuid.uuid4().hex[:6]}@example.com"
    password = "clave-ui-segura-123"  # nosec B105  # NOSONAR: credencial de prueba de una cuenta efimera

    def code_from_inbox(prefix):
        for _ in range(40):
            with urllib.request.urlopen(f"{MAILPIT}/api/v1/messages", timeout=10) as r:  # nosec B310
                msgs = json.load(r).get("messages", [])
            for m in msgs:
                if any(t["Address"] == email for t in m["To"]) and (m.get("Subject") or "").startswith(prefix):
                    return m["Subject"].rsplit(" ", 1)[-1]
            pg.wait_for_timeout(500)
        return None

    # Registro con codigo por correo
    pg.click("text=Crear una cuenta"); pg.fill("#login-username", "Viajero UI")
    pg.fill("#auth-email", email); pg.fill("#auth-password", password)
    pg.locator("form.login button[type=submit]").click()
    pg.wait_for_selector("text=Verifica tu correo"); log(True, "registro: pide el codigo de verificacion")
    pg.screenshot(path=str(SHOTS / "verificacion.png"))
    pg.fill("#login-username", "000000"); pg.locator("form.login button[type=submit]").click()
    pg.wait_for_selector("text=incorrecto"); log(True, "codigo incorrecto se rechaza con mensaje")
    code = code_from_inbox("Tu código de verificación"); log(bool(code), "el codigo llega por correo (Mailpit)")
    pg.fill("#login-username", code); pg.locator("form.login button[type=submit]").click()
    pg.wait_for_selector("text=Mis itinerarios"); log(True, "verificado: entra con sesion iniciada")
    pg.wait_for_selector("text=Tu cuenta no tiene un correo verificado", state="detached", timeout=3000)
    # La sesion sobrevive al refrescar (cookie httpOnly) y no hay nada en el almacenamiento del navegador
    pg.reload(); pg.wait_for_selector("text=Mis itinerarios"); log(True, "refrescar la pagina conserva la sesion")
    log(pg.evaluate("document.cookie.includes('itinerarios_session')") is False, "la cookie de sesion no es legible desde JavaScript")
    log(pg.evaluate("localStorage.length + sessionStorage.length") == 0, "nada de tokens en localStorage/sessionStorage")
    pg.click("text=Cerrar sesión"); pg.wait_for_selector("text=Inicia sesión"); log(True, "cerrar sesion")
    pg.reload(); pg.wait_for_selector("text=Inicia sesión"); log(True, "tras cerrar sesion, refrescar NO la recupera")
    pg.fill("#login-username", email); pg.fill("#auth-password", "contraseña-equivocada-1")
    pg.locator("form.login button[type=submit]").click(); pg.wait_for_selector("text=incorrectos"); log(True, "contrasena incorrecta se rechaza")
    pg.fill("#auth-password", password); pg.locator("form.login button[type=submit]").click()
    pg.wait_for_selector("text=Mis itinerarios"); log(True, "login con correo y contrasena")
    pg.click("button:has-text('Nuevo')")
    form=pg.locator("form:has-text('Nuevo vuelo')")
    opts=form.locator("select").first.locator("option").all_inner_texts()
    def pick(sel_idx,iata):
        s=form.locator("select").nth(sel_idx); v=[o for o in s.locator("option").all() if f"({iata})" in o.inner_text()][0].get_attribute("value"); s.select_option(v)
    def fly(o,d,hhmm):
        pick(0,o); pick(1,d); form.locator("input[type=datetime-local]").fill(f"{day}T{hhmm}")
    fly("BOG","MDE","06:00"); pg.wait_for_timeout(300)
    txt=form.inner_text(); log("Llegas el" in txt, "muestra llegada calculada: "+re.search(r"Llegas el[^\n]*",txt).group(0)[:80] if "Llegas el" in txt else "sin llegada")
    form.locator("input[type=number]").fill("120")
    form.locator("button[type=submit]").click(); pg.wait_for_selector("text=1 itinerario"); log(True,"vuelo BOG→MDE 06:00 (120 min) guardado")
    pg.screenshot(path=str(SHOTS / "lista.png"))
    # conflicto: salir de otra ciudad a las 07:00
    pg.click("button:has-text('Nuevo')") if not pg.locator("form:has-text('Nuevo vuelo')").count() else None
    form=pg.locator("form:has-text('Nuevo vuelo')")
    log("Tu último vuelo llega a" in form.inner_text(),"sugerencia de dónde puedes salir")
    fly("CTG","BOG","07:00"); pg.wait_for_timeout(300)
    t=form.inner_text(); log("Se cruza" in t,"aviso de traslape en pantalla")
    log(form.locator("button[type=submit]").is_disabled(),"botón Guardar bloqueado con conflicto")
    pg.screenshot(path=str(SHOTS / "conflicto.png"))
    fly("CTG","BOG","09:00"); pg.wait_for_timeout(300); t=form.inner_text()
    log("anterior llega a" in t,"aviso de ciudad incorrecta")
    form.locator('button.link-btn').click()
    pick(1,"BOG"); form.locator("input[type=datetime-local]").fill(f"{day}T08:00"); pg.wait_for_timeout(300)
    log(not form.locator("button[type=submit]").is_disabled() and "Se cruza" not in form.inner_text(),"salir de la ciudad de llegada a las 08:00 es válido")
    form.locator("button[type=submit]").click(); pg.wait_for_selector("text=2 itinerarios"); log(True,"segundo vuelo MDE→BOG guardado")
    pg.screenshot(path=str(SHOTS / "panel-dos-vuelos-encadenados.png"), full_page=True)
    pg.set_viewport_size({"width":390,"height":844}); pg.wait_for_timeout(300); pg.screenshot(path=str(SHOTS / "panel-movil.png"), full_page=True)
    log(not errs,"sin errores en consola" if not errs else "errores consola: "+"; ".join(errs[:3]))
    b.close()
