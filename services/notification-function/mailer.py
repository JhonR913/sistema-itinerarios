"""Envio SMTP de recordatorios. En desarrollo apunta a Mailpit
(`SMTP_HOST=mailpit`, puerto 1025, sin autenticacion ni TLS)."""
import os
import smtplib
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo
from email.message import EmailMessage


def build_reminder(sender: str, to: str, nombre: str, origin: str, destination: str,
                   travel_date: date, itinerary_id: str, tz_name: str,
                   departure_at: Optional[datetime] = None, arrival_at: Optional[datetime] = None,
                   origin_city: Optional[str] = None, destination_city: Optional[str] = None) -> EmailMessage:
    msg = EmailMessage()  # rechaza saltos de linea en cabeceras (anti header-injection)
    msg["From"] = sender
    msg["To"] = to
    msg["X-Itinerary-Id"] = itinerary_id
    tz = ZoneInfo(tz_name)
    de = f"{origin_city} ({origin})" if origin_city else origin
    a = f"{destination_city} ({destination})" if destination_city else destination
    if departure_at is not None:
        dep = departure_at.astimezone(tz)
        msg["Subject"] = f"Recordatorio de vuelo {origin} - {destination}: {dep:%d/%m/%Y %H:%M}"
        lines = [f"Hola {nombre},", "",
                 f"Tu vuelo de {de} a {a} sale el {dep:%d/%m/%Y} a las {dep:%H:%M}."]
        if arrival_at is not None:
            arr = arrival_at.astimezone(tz)
            lines.append(f"Llegada estimada: {arr:%d/%m/%Y} a las {arr:%H:%M}.")
        lines += [f"(Horas en zona horaria {tz_name}.)", "",
                  "Recuerda llegar con tiempo al aeropuerto y llevar tu documento de identidad.", ""]
    else:  # eventos antiguos sin hora
        msg["Subject"] = f"Recordatorio de viaje {origin} - {destination} el {travel_date.isoformat()}"
        lines = [f"Hola {nombre},", "",
                 f"Te recordamos tu viaje de {origin} a {destination} el {travel_date.isoformat()} "
                 f"(fecha segun la zona horaria {tz_name}).", ""]
    msg.set_content("\n".join(lines) + "\nSistema de Itinerarios Personales\n")
    return msg


def send(msg: EmailMessage) -> None:
    host = os.environ.get("SMTP_HOST", "mailpit")
    port = int(os.environ.get("SMTP_PORT", "1025"))
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if os.environ.get("SMTP_STARTTLS", "0") == "1":
            smtp.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
