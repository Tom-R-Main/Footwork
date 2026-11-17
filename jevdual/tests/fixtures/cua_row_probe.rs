//! Offline AX-provider adapter: production schema and recipient validator, no OS input.
use cua_driver_contract::row::{discover_row, dispatch_row, RowBinding, RowGraph};
use cua_driver_contract::{ActionTarget, ClickInput, ToolInput};
use std::io::{self, Read};
fn main() {
    let mut text = String::new();
    io::stdin().read_to_string(&mut text).unwrap();
    let input: serde_json::Value = serde_json::from_str(&text).unwrap();
    if input["mode"] == "discover" {
        let graph: RowGraph = serde_json::from_value(input["graph"].clone()).unwrap();
        let result = discover_row(
            &graph,
            input["pid"].as_u64().unwrap() as u32,
            input["window_id"].as_u64().unwrap(),
            input["recipient"].as_u64().unwrap(),
        );
        println!(
            "{}",
            match result {
                Ok(binding) => serde_json::json!({"binding":binding}),
                Err(error) => serde_json::json!({"binding":null,"error":error}),
            }
        );
        return;
    }
    let parsed = serde_json::from_value::<ClickInput>(input["click"].clone())
        .map_err(|e| e.to_string())
        .and_then(|i| {
            i.validate()?;
            Ok(i)
        });
    let click = match parsed {
        Ok(click) => click,
        Err(error) => {
            println!(
                "{}",
                serde_json::json!({"schema_valid":false,"error":error,"presses":[]})
            );
            return;
        }
    };
    if input["mode"] != "dispatch" {
        println!("{}", serde_json::json!({"schema_valid":true}));
        return;
    }
    let binding: RowBinding = serde_json::from_value(input["binding"].clone()).unwrap();
    let graph =
        serde_json::from_value::<RowGraph>(input["graph"].clone()).map_err(|e| e.to_string());
    let ActionTarget::Window { pid, window_id } = click.target else {
        panic!("fixture requires window")
    };
    let recipient = input["recipient"].as_u64().unwrap();
    let mut presses = Vec::new();
    let receipt = dispatch_row(
        graph,
        &binding,
        click.expected_row.as_ref(),
        pid,
        window_id,
        recipient,
        || {
            if input["admission_error"] == true {
                Err("fixture focus lost before press".into())
            } else {
                Ok(())
            }
        },
        || {
            presses.push(recipient);
            if input["press_error"] == true {
                Err("fixture AXPress response lost".into())
            } else {
                Ok(())
            }
        },
    );
    println!(
        "{}",
        serde_json::json!({"schema_valid":true,"receipt":receipt,"presses":presses})
    );
}
