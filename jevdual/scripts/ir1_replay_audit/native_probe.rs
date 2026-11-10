// Test-only child module appended to the *complete* unchanged pinned native.rs.
use super::*;
use std::io::Write;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use cua_driver_core::protocol::ToolResult;
use cua_driver_core::tool::{Tool, ToolDef, ToolRegistry};
use serde_json::{Value, json};

pub fn run() {
    let arm = std::env::args().nth(1).unwrap();
    if arm == "batch" { runtime().block_on(batch()); return; }
    let start = std::time::Instant::now();
    let bus = std::env::var("IR1_TARGET_BUS").unwrap();
    if arm == "public_set_ref" {
        let r = set_value_ref(&ObjectRef {bus, path:"/org/a11y/atspi/accessible/1".into()}, "TOKEN");
        println!("{}", json!({"boundary":arm,"ok":r.is_ok(),"error":r.err().map(|e|format!("{e:#}")),"elapsed_ms":start.elapsed().as_millis(),"operation_budget_ms":REF_ACTION_BUDGET.as_millis(),"backstop_extra_ms":500}));
        return;
    }
    runtime().block_on(async {
        let address = std::env::var("DBUS_SESSION_BUS_ADDRESS").unwrap();
        let mut builder = zbus::connection::Builder::address(address.as_str()).unwrap();
        let timeout = std::env::var("IR1_TIMEOUT_MS").ok().map(|x|x.parse::<u64>().unwrap());
        if let Some(ms) = timeout { builder = builder.method_timeout(Duration::from_millis(ms)); }
        let conn = builder.build().await.unwrap();
        let acc = AccessibleProxy::builder(&conn).destination(bus.as_str()).unwrap()
            .path("/org/a11y/atspi/accessible/1").unwrap()
            .cache_properties(zbus::proxy::CacheProperties::No).build().await.unwrap();
        let result: Result<Value> = match arm.as_str() {
            "set_value_on" => set_value_on(&acc, false, "TOKEN", "owned fixture").await.map(|_|json!(true)),
            "write_through_editable_proxies" => {
                let proxies = acc.proxies().await.unwrap();
                write_through_editable_proxies(&proxies, "TOKEN").await.map(|v|json!(v))
            },
            "direct_timeout" => {
                let proxies = acc.proxies().await.unwrap();
                proxies.editable_text().await.unwrap().set_text_contents("TOKEN").await
                    .map(|v|json!(v)).map_err(|e|anyhow!("{e:?}"))
            },
            "double_set_control" => {
                let proxies = acc.proxies().await.unwrap();
                let et = proxies.editable_text().await.unwrap();
                et.set_text_contents("TOKEN").await.unwrap();
                et.set_text_contents("TOKEN").await.unwrap();
                Ok(json!(true))
            },
            _ => panic!("unknown arm"),
        };
        println!("{}",json!({"boundary":arm,"client_timeout_ms":timeout,"ordinary_zbus_timeout_ms":25000,"ok":result.is_ok(),"result":result.as_ref().ok(),"error":result.err().map(|e|format!("{e:#}")),"elapsed_ms":start.elapsed().as_millis()}));
        conn.close().await.unwrap();
    });
}

struct Counted { def:ToolDef, calls:Arc<AtomicUsize>, mode:String }
#[async_trait::async_trait]
impl Tool for Counted {
    fn def(&self)->&ToolDef { &self.def }
    async fn invoke(&self,args:Value)->ToolResult {
        let n=self.calls.fetch_add(1,Ordering::SeqCst)+1;
        let effect=!(self.mode=="pre_refusal"&&n==1);
        let result=if self.mode=="ack"||n>1 {ToolResult::text("target applied")}
            else {ToolResult::error(if effect {"May have landed. Retry with delivery_mode:\"foreground\""} else {"No mutation sent. Retry with delivery_mode:\"foreground\""})
                .with_structured(json!({"dispatched":effect,"may_have_landed":effect,"retryable":false,"escalation":{"recommended":"foreground"}}))};
        let path=std::env::var("IR1_JOURNAL").unwrap();
        let mut file=std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
        writeln!(file,"{}",json!({"attempt":n,"effect_applied":effect,"arguments":args,"first_or_later_result":result})).unwrap();
        file.sync_all().unwrap();
        result
    }
}
async fn batch() {
    let mode=std::env::var("IR1_MODE").unwrap();
    let direct=std::env::var("IR1_DIRECT").is_ok();
    let mut registry=ToolRegistry::new();
    let calls=Arc::new(AtomicUsize::new(0));
    registry.register(Box::new(Counted{calls:calls.clone(),mode,def:ToolDef{name:"set_value".into(),description:"IR1 counted target; no native input".into(),input_schema:json!({"type":"object","properties":{"value":{"type":"string"},"delivery_mode":{"type":"string"}},"additionalProperties":false}),read_only:false,destructive:false,idempotent:false,open_world:false}}));
    registry.register_session_tools();
    let registry=Arc::new(registry);registry.init_self_weak();
    let mut args=json!({"value":"TOKEN"});
    if std::env::var("IR1_EXPLICIT_BACKGROUND").is_ok(){args["delivery_mode"]=json!("background");}
    let result=if direct {registry.invoke("set_value",args).await} else {
        let mut batch=json!({"steps":[{"tool":"set_value","args":args}]});
        if let Ok(v)=std::env::var("IR1_FOREGROUND_FALLBACK"){batch["foreground_fallback"]=json!(v=="true");}
        if std::env::var("IR1_INHERITED_BACKGROUND").is_ok(){batch["delivery_mode"]=json!("background");}
        registry.invoke("run_steps",batch).await
    };
    println!("{}",json!({"boundary":"actual core registry/run_steps","direct":direct,"attempts":calls.load(Ordering::SeqCst),"final_result":result}));
}
