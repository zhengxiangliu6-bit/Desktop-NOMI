import {
  emotions,
  emotionLabels,
  phases,
  phaseLabels,
  type Emotion,
  type Phase,
  type RobotState,
} from "./model";
import { mapExpression } from "../../adapters/expression/mapExpression";

interface Props {
  state: RobotState;
  disabled: boolean;
  onPreview: (phase: Exclude<Phase, "error">, emotion: Emotion) => void;
  onError: () => void;
}
export function DebugPanel({ state, disabled, onPreview, onError }: Props) {
  return (
    <details className="debug-panel">
      <summary>
        <span>开发调试</span>
        <span className="debug-caption">状态与表情预览</span>
      </summary>
      <div className="debug-content">
        <p>纯本地演示；倾听不录音，回复不播放声音。预览 2.4 秒后恢复待机。</p>
        <dl>
          <div>
            <dt>交互阶段</dt>
            <dd>{state.phase}</dd>
          </div>
          <div>
            <dt>情绪</dt>
            <dd>{state.emotion}</dd>
          </div>
          <div>
            <dt>Aora state</dt>
            <dd>{mapExpression(state.phase, state.emotion)}</dd>
          </div>
        </dl>
        <fieldset disabled={disabled}>
          <legend>交互阶段</legend>
          <div className="debug-buttons">
            {phases
              .filter((p) => p !== "error")
              .map((p) => (
                <button key={p} onClick={() => onPreview(p, "neutral")}>
                  {phaseLabels[p]}
                </button>
              ))}
            <button onClick={onError}>模拟错误</button>
          </div>
        </fieldset>
        <fieldset disabled={disabled}>
          <legend>情绪表情</legend>
          <div className="debug-buttons">
            {emotions.map((e) => (
              <button key={e} onClick={() => onPreview("idle", e)}>
                {emotionLabels[e]}
              </button>
            ))}
          </div>
        </fieldset>
      </div>
    </details>
  );
}
