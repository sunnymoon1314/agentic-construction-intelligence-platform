mod app;
mod components;
mod models;

use app::App;
use leptos::*;

fn main() {
    // Set up console panic hook for browser debugging
    console_error_panic_hook::set_once();
    _ = console_log::init_with_level(log::Level::Debug);

    // Mount the Leptos reactive application to the browser DOM
    mount_to_body(|| view! { <App/> })
}
