import { Icon } from "../../components/ui/Icon";
import { SessionMenu } from "../auth/SessionMenu";

/** Barra superior: identidad, navegación interna de la página y estado de sesión. */
export function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar__inner">
        <a className="brand" href="#mapa" aria-label="Sistema de Itinerarios Personales">
          <span className="brand__mark" aria-hidden="true">
            <Icon name="plane" size={20} />
          </span>
          <span className="brand__name">
            Itinerarios<span className="brand__sub"> Personales</span>
          </span>
        </a>

        <nav className="topbar__nav" aria-label="Secciones">
          <a href="#mapa">Mapa</a>
          <a href="#itinerarios">Itinerarios</a>
        </nav>

        <SessionMenu />
      </div>
    </header>
  );
}
