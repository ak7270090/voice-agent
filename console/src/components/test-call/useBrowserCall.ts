"use client";

// One LiveKit room per test call. Typed messages go to the agent on the lk.chat text stream;
// replies and voice transcripts come back on lk.transcription. The mic button asks the agent
// (RPC set_voice) to start listening and speaking, and publishes the tester's microphone.
import {
  DisconnectReason,
  type Participant,
  type RemoteTrack,
  Room,
  RoomEvent,
  type TextStreamReader,
  Track,
} from "livekit-client";
import { useCallback, useEffect, useRef, useState } from "react";

import { startBrowserCall } from "@/lib/api";

const CHAT_TOPIC = "lk.chat";
const TRANSCRIPTION_TOPIC = "lk.transcription";
const SEGMENT_ID_ATTRIBUTE = "lk.segment_id";
const FINAL_ATTRIBUTE = "lk.transcription_final";
const AGENT_STATE_ATTRIBUTE = "lk.agent.state";
const SET_VOICE_METHOD = "set_voice";

export type CallStatus = "idle" | "connecting" | "connected";
export type AgentState = "initializing" | "listening" | "thinking" | "speaking" | string;

export type ChatMessage = {
  id: string;
  speaker: "agent" | "tester";
  text: string;
  via?: "typed" | "said";
  interim: boolean;
};

export function useBrowserCall(agentId: string) {
  const roomRef = useRef<Room | null>(null);
  const audioElements = useRef<HTMLMediaElement[]>([]);
  const [status, setStatus] = useState<CallStatus>("idle");
  const [agentState, setAgentState] = useState<AgentState>("initializing");
  const [voiceOn, setVoiceOn] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const upsertMessage = useCallback((message: ChatMessage) => {
    setMessages((current) => {
      const index = current.findIndex((existing) => existing.id === message.id);
      if (index === -1) return [...current, message];
      const next = [...current];
      next[index] = message;
      return next;
    });
  }, []);

  // The agent writes each reply as one stream of text deltas; a voice transcript is re-sent in
  // full while the tester speaks. Either way the latest stream for a segment holds its text.
  const showTranscription = useCallback(
    async (reader: TextStreamReader, sender: { identity: string }) => {
      const room = roomRef.current;
      const id = reader.info.attributes?.[SEGMENT_ID_ATTRIBUTE] ?? reader.info.id;
      const fromTester = sender.identity === room?.localParticipant.identity;
      const final = reader.info.attributes?.[FINAL_ATTRIBUTE] === "true";
      const speaker = fromTester ? "tester" : "agent";
      const via = fromTester ? "said" : undefined;
      let text = "";
      try {
        for await (const chunk of reader) {
          text += chunk;
          upsertMessage({ id, speaker, text, via, interim: fromTester && !final });
        }
      } finally {
        upsertMessage({ id, speaker, text, via, interim: false });
      }
    },
    [upsertMessage],
  );

  const cleanUp = useCallback(() => {
    audioElements.current.forEach((element) => element.remove());
    audioElements.current = [];
    roomRef.current = null;
    setStatus("idle");
    setVoiceOn(false);
    setAgentState("initializing");
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setMessages([]);
    setStatus("connecting");
    try {
      const { url, token } = await startBrowserCall(agentId);
      const room = new Room();
      roomRef.current = room;
      room.registerTextStreamHandler(TRANSCRIPTION_TOPIC, showTranscription);
      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
        if (track.kind !== Track.Kind.Audio) return;
        const element = track.attach();
        document.body.append(element);
        audioElements.current.push(element);
      });
      room.on(
        RoomEvent.ParticipantAttributesChanged,
        (changed: Record<string, string>, participant: Participant) => {
          if (participant.isAgent && AGENT_STATE_ATTRIBUTE in changed) {
            setAgentState(changed[AGENT_STATE_ATTRIBUTE]);
          }
        },
      );
      room.on(RoomEvent.Disconnected, (reason?: DisconnectReason) => {
        if (reason !== DisconnectReason.CLIENT_INITIATED) {
          setError("The connection dropped, so the call ended. Start it again.");
        }
        cleanUp();
      });
      await room.connect(url, token);
      setStatus("connected");
    } catch (cause) {
      setError(`Could not connect: ${(cause as Error).message}. Is the runtime running?`);
      roomRef.current?.disconnect();
      cleanUp();
    }
  }, [agentId, cleanUp, showTranscription]);

  const end = useCallback(() => roomRef.current?.disconnect(), []);

  const send = useCallback(
    async (text: string) => {
      const room = roomRef.current;
      if (!room || !text.trim()) return;
      upsertMessage({
        id: crypto.randomUUID(),
        speaker: "tester",
        text: text.trim(),
        via: "typed",
        interim: false,
      });
      await room.localParticipant.sendText(text.trim(), { topic: CHAT_TOPIC });
    },
    [upsertMessage],
  );

  const toggleVoice = useCallback(async () => {
    const room = roomRef.current;
    const agent = room && [...room.remoteParticipants.values()].find((p) => p.isAgent);
    if (!room || !agent) return;
    const enable = !voiceOn;
    try {
      await room.localParticipant.setMicrophoneEnabled(enable);
      await room.localParticipant.performRpc({
        destinationIdentity: agent.identity,
        method: SET_VOICE_METHOD,
        payload: enable ? "on" : "off",
      });
      setVoiceOn(enable);
    } catch (cause) {
      setError(`Microphone: ${(cause as Error).message}`);
    }
  }, [voiceOn]);

  useEffect(() => () => void roomRef.current?.disconnect(), []);

  return { status, agentState, voiceOn, messages, error, start, end, send, toggleVoice };
}
