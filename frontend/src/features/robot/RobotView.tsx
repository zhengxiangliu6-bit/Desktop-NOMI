import { Component, type ReactNode } from "react";
import { CharacterMark } from "@aora-bot/react";
import { mapExpression } from "../../adapters/expression/mapExpression";
import { emotionLabels, phaseLabels, type Emotion, type Phase } from "./model";

class ExpressionBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div
        className="face-fallback"
        role="img"
        aria-label="机器人表情暂时不可用"
      >
        ◡
      </div>
    ) : (
      this.props.children
    );
  }
}
export function RobotView({
  phase,
  emotion,
}: {
  phase: Phase;
  emotion: Emotion;
}) {
  return (
    <section className="robot-world" aria-label="虚拟机器人">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <span className="world-note">YOUR LITTLE DESKTOP COMPANION</span>
      <div
        className="robot-stage"
        role="img"
        aria-label={`NOMI，${phaseLabels[phase]}，${emotionLabels[emotion]}`}
      >
        <ExpressionBoundary>
          <CharacterMark
            shape="circle"
            color="cream"
            face="cute"
            state={mapExpression(phase, emotion)}
            sizeCss="clamp(210px, 30vw, 310px)"
            followPointer={false}
            autoPause={true}
          />
        </ExpressionBoundary>
      </div>
      <div className="ground-shadow" />
      <div className="robot-status" role="status" aria-live="polite">
        <span className={`status-dot ${phase}`} />
        {phaseLabels[phase]}
      </div>
      <p className="emotion-caption">小小情绪 · {emotionLabels[emotion]}</p>
    </section>
  );
}
