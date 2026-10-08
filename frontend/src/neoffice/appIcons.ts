// //// Neoffice — added file (no upstream equivalent): the brand's icon of each Suite app (maintenance#1316).
// //// The same Streamline icons as the cockpit's switcher and every other Neoffice app (decided 27.09, store and
// //// table in neoffice_theme/public/icons/streamline/README.md, served to the cockpit as neoffice_app_icons).
// //// neoffice_theme serves the files: Streamline's licence keeps them out of this public repository, which
// //// only names their address.
const STREAMLINE = '/assets/neoffice_theme/icons/streamline'

export const NEOFFICE_APP_ICONS = {
  drive: `${STREAMLINE}/cloud-folder.svg`,
  calendar: `${STREAMLINE}/calendar.svg`,
  meet: `${STREAMLINE}/video-camera.svg`,
  mail: `${STREAMLINE}/envelope.svg`,
  sheets: `${STREAMLINE}/table.svg`,
  slides: `${STREAMLINE}/monitor.svg`,
  writer: `${STREAMLINE}/document.svg`,
  settings: `${STREAMLINE}/gear.svg`,
  // the launcher's own mark: Neoffice's
  suite: '/assets/neoffice_theme/images/neoffice_icon.png',
} as const
