#!/usr/bin/env python3
"""Prueba visual del flujo de agenda con un navegador real (Playwright/Chromium).
Requiere el sistema levantado y el frontend servido en http://localhost:8080 con /api/* enrutado
(Traefik en Compose). Crea un viajero nuevo en cada corrida. No esta integrada al CI."""
import re, sys
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
BOG=timezone(timedelta(hours=-5))
day=(datetime.now(BOG)+timedelta(days=15)).strftime("%Y-%m-%d")
def log(ok,msg): print(("[OK] " if ok else "[FALLA] ")+msg, flush=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1400,"height":950})
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e))); pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto("http://localhost:8080/"); pg.wait_for_selector("#login-username")
    import uuid; pg.fill("#login-username","viajero-"+uuid.uuid4().hex[:5]); pg.fill("#login-email","viajero@example.com")
    pg.locator('form.login button[type=submit]').click()
    pg.wait_for_selector("text=Mis itinerarios"); log(True,"login con correo")
    pg.wait_for_selector("text=Sin correo", state="detached", timeout=3000)
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
    pg.screenshot(path="/tmp/ui/1-lista.png")
    # conflicto: salir de otra ciudad a las 07:00
    pg.click("button:has-text('Nuevo')") if not pg.locator("form:has-text('Nuevo vuelo')").count() else None
    form=pg.locator("form:has-text('Nuevo vuelo')")
    log("Tu último vuelo llega a" in form.inner_text(),"sugerencia de dónde puedes salir")
    fly("CTG","BOG","07:00"); pg.wait_for_timeout(300)
    t=form.inner_text(); log("Se cruza" in t,"aviso de traslape en pantalla")
    log(form.locator("button[type=submit]").is_disabled(),"botón Guardar bloqueado con conflicto")
    pg.screenshot(path="/tmp/ui/2-conflicto.png")
    fly("CTG","BOG","09:00"); pg.wait_for_timeout(300); t=form.inner_text()
    log("anterior llega a" in t,"aviso de ciudad incorrecta")
    form.locator('button.link-btn').click()
    pick(1,"BOG"); form.locator("input[type=datetime-local]").fill(f"{day}T08:00"); pg.wait_for_timeout(300)
    log(not form.locator("button[type=submit]").is_disabled() and "Se cruza" not in form.inner_text(),"salir de la ciudad de llegada a las 08:00 es válido")
    form.locator("button[type=submit]").click(); pg.wait_for_selector("text=2 itinerarios"); log(True,"segundo vuelo MDE→BOG guardado")
    pg.screenshot(path="/tmp/ui/3-dos-vuelos.png", full_page=True)
    pg.set_viewport_size({"width":390,"height":844}); pg.wait_for_timeout(300); pg.screenshot(path="/tmp/ui/4-movil.png", full_page=True)
    log(not errs,"sin errores en consola" if not errs else "errores consola: "+"; ".join(errs[:3]))
    b.close()
