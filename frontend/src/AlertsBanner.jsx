import { alertColor, formatEffect } from "./alertFormat";

export function AlertsBanner({ alerts }) {
  if (alerts.length === 0) return null;

  return (
    <div className="alerts-banner">
      {alerts.map((alert) => (
        <div
          key={alert.alert_id}
          className="alert-row"
          style={{ borderLeftColor: alertColor(alert.severity) }}
        >
          <span className="alert-effect" style={{ color: alertColor(alert.severity) }}>
            {formatEffect(alert.effect)}
          </span>
          <span className="alert-header">{alert.header}</span>
        </div>
      ))}
    </div>
  );
}
