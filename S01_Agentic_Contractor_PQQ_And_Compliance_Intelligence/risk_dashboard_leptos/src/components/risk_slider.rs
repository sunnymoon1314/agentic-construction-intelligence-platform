use leptos::*;

#[component]
pub fn RiskSlider(
    label: &'static str,
    value: ReadSignal<f64>,
    set_value: WriteSignal<f64>,
    min: f64,
    max: f64,
    step: f64,
    unit: &'static str,
    color_accent: &'static str,
    #[prop(default = "")] info: &'static str,
) -> impl IntoView {
    view! {
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 0.82rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                    {label}
                    {if !info.is_empty() {
                        view! {
                            <span title=info style="cursor: help; font-size: 0.8rem; opacity: 0.85;">"ℹ️"</span>
                        }.into_view()
                    } else {
                        view! { <span></span> }.into_view()
                    }}
                </span>
                <span style=format!("font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; font-weight: 600; color: {};", color_accent)>
                    {move || {
                        let v = value.get();
                        if unit == "SGD" {
                            format!("S${:.1}M", v / 1_000_000.0)
                        } else if unit == "%" {
                            format!("{:.1}%", v)
                        } else {
                            format!("{:.0} {}", v, unit)
                        }
                    }}
                </span>
            </div>
            <input
                type="range"
                min=min.to_string()
                max=max.to_string()
                step=step.to_string()
                prop:value=move || value.get().to_string()
                on:input=move |ev| {
                    if let Ok(new_val) = event_target_value(&ev).parse::<f64>() {
                        set_value.set(new_val);
                    }
                }
                style="width: 100%; height: 6px; border-radius: 3px; background: var(--slider-track); outline: none; cursor: pointer; accent-color: #2563eb;"
            />
        </div>
    }
}
