//! Offline adapter fixture. No OS access; production schema is not mocked.
use std::io::{self, Read};
use cua_driver_contract::{ClickInput, ToolInput};
fn main() {
    let mut text = String::new(); io::stdin().read_to_string(&mut text).unwrap();
    let input: serde_json::Value = serde_json::from_str(&text).unwrap();
    let result = serde_json::from_value::<ClickInput>(input["click"].clone())
        .map_err(|e| e.to_string()).and_then(|i| i.validate());
    println!("{}", serde_json::json!({"schema_valid": result.is_ok(), "error": result.err(), "presses": []}));
}
