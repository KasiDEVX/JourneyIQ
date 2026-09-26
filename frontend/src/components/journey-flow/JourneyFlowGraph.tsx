// src/components/journey-flow/JourneyFlowGraph.tsx
//
// Interactive Customer Journey Flow Graph (Stage 7).
// Represents actual reconstructed customer journeys and cross-channel transitions.
//
// DESIGN SPECIFICATIONS:
// - Background: Warm ivory / light gray
// - Nodes: White / Graphite design system (no rainbow/neon fills)
// - Start Node: Graphite
// - Channel Nodes: Crisp White with dark graphite typography
// - Conversion Node: Emerald accent card
// - Links: Slate with controlled opacity
// - Active Links (hover/focused): JourneyIQ Coral (#FF5722)
// - Directional links with proportional thickness
// - Keyboard accessible controls & responsive horizontal scroll on mobile

import React, {
  useMemo,
  useState,
  useCallback,
  useRef,
  useEffect,
} from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Move,
} from 'lucide-react';
import { JourneyFlowNode, JourneyFlowLink, JourneyFlowResponse } from '@/types/analytics';
import { JourneyFlowTooltip, TooltipData } from './JourneyFlowTooltip';
import { JourneyFlowInspector } from './JourneyFlowInspector';

const START_ID = '__START__';
const CONVERSION_ID = '__CONVERSION__';

// Visual layout constants
const NODE_WIDTH = 142;
const NODE_HEIGHT = 42;
const NODE_RADIUS = 8;
const PADDING_X = 36;
const PADDING_TOP = 52;
const PADDING_BOTTOM = 28;
const MIN_LINK_THICKNESS = 2;
const MAX_LINK_THICKNESS = 22;

interface LayoutNode {
  node: JourneyFlowNode;
  layer: number;
  x: number;
  y: number;
  totalIn: number;
  totalOut: number;
}

interface LayoutLink {
  link: JourneyFlowLink;
  sourceLayout: LayoutNode;
  targetLayout: LayoutNode;
  thickness: number;
  sourceY: number;
  targetY: number;
}

interface StageHeader {
  label: string;
  sublabel: string;
  x: number;
}

function computeLayout(
  data: JourneyFlowResponse,
  svgWidth: number,
  compact: boolean = false,
): { nodes: LayoutNode[]; links: LayoutLink[]; svgHeight: number; stageHeaders: StageHeader[] } {
  if (data.nodes.length === 0) {
    return { nodes: [], links: [], svgHeight: compact ? 220 : 340, stageHeaders: [] };
  }

  const inFlow = new Map<string, number>();
  const outFlow = new Map<string, number>();
  for (const node of data.nodes) {
    inFlow.set(node.id, 0);
    outFlow.set(node.id, 0);
  }
  for (const link of data.links) {
    inFlow.set(link.target, (inFlow.get(link.target) ?? 0) + link.value);
    outFlow.set(link.source, (outFlow.get(link.source) ?? 0) + link.value);
  }

  const hasConversion = data.nodes.some((n) => n.id === CONVERSION_ID);
  const channelNodes = data.nodes.filter((n) => n.type === 'channel');

  const sortedChannels = [...channelNodes].sort((a, b) => {
    const startA = data.links.find((l) => l.source === START_ID && l.target === a.id)?.value ?? 0;
    const startB = data.links.find((l) => l.source === START_ID && l.target === b.id)?.value ?? 0;
    return startB - startA;
  });

  const layerMap = new Map<string, number>();
  layerMap.set(START_ID, 0);

  let numStages = 3;
  if (channelNodes.length > 5 && !compact) {
    numStages = hasConversion ? 4 : 3;
    const half = Math.ceil(sortedChannels.length / 2);
    sortedChannels.forEach((ch, idx) => {
      layerMap.set(ch.id, idx < half ? 1 : 2);
    });
    if (hasConversion) {
      layerMap.set(CONVERSION_ID, 3);
    }
  } else {
    numStages = hasConversion ? 3 : 2;
    sortedChannels.forEach((ch) => {
      layerMap.set(ch.id, 1);
    });
    if (hasConversion) {
      layerMap.set(CONVERSION_ID, 2);
    }
  }

  const byLayer = new Map<number, JourneyFlowNode[]>();
  for (let i = 0; i < numStages; i++) {
    byLayer.set(i, []);
  }

  for (const node of data.nodes) {
    const layer = layerMap.get(node.id) ?? 1;
    if (byLayer.has(layer)) {
      byLayer.get(layer)!.push(node);
    }
  }

  for (const [layerIdx, nodes] of byLayer) {
    if (layerIdx === 0 || (hasConversion && layerIdx === numStages - 1)) {
      continue;
    }
    nodes.sort((a, b) => {
      const flowA = (inFlow.get(a.id) ?? 0) + (outFlow.get(a.id) ?? 0);
      const flowB = (inFlow.get(b.id) ?? 0) + (outFlow.get(b.id) ?? 0);
      return flowB - flowA;
    });
  }

  let maxNodesInLayer = 1;
  for (const [, nodes] of byLayer) {
    maxNodesInLayer = Math.max(maxNodesInLayer, nodes.length);
  }

  const V_GAP = compact ? (maxNodesInLayer > 6 ? 6 : 8) : maxNodesInLayer > 6 ? 10 : 14;
  const currentHeight = maxNodesInLayer * NODE_HEIGHT + (maxNodesInLayer - 1) * V_GAP;
  const minBaseHeight = compact ? 260 : 380;
  const svgHeight = Math.max(minBaseHeight, PADDING_TOP + currentHeight + PADDING_BOTTOM);

  const usableWidth = svgWidth - PADDING_X * 2 - NODE_WIDTH;
  const colStep = numStages <= 1 ? 0 : usableWidth / (numStages - 1);

  const layoutNodes: LayoutNode[] = [];
  const layoutByID = new Map<string, LayoutNode>();
  const stageHeaders: StageHeader[] = [];

  for (let layerIdx = 0; layerIdx < numStages; layerIdx++) {
    const nodes = byLayer.get(layerIdx) || [];
    const totalHeight = nodes.length * NODE_HEIGHT + (nodes.length - 1) * V_GAP;
    const startY = PADDING_TOP + (svgHeight - PADDING_TOP - PADDING_BOTTOM - totalHeight) / 2;
    const x = PADDING_X + layerIdx * colStep;

    let label = 'Touchpoints';
    let sublabel = 'Channel steps';
    if (layerIdx === 0) {
      label = '1. Entry';
      sublabel = 'Journey origin';
    } else if (layerIdx === numStages - 1 && hasConversion) {
      label = `${numStages}. Conversion`;
      sublabel = 'Goal reached';
    } else if (numStages === 4 && layerIdx === 1) {
      label = '2. Discovery';
      sublabel = 'Initial touch';
    } else if (numStages === 4 && layerIdx === 2) {
      label = '3. Nurturing';
      sublabel = 'Follow-up touch';
    } else {
      label = '2. Channels';
      sublabel = 'Cross-channel flow';
    }

    stageHeaders.push({
      label,
      sublabel,
      x: x + NODE_WIDTH / 2,
    });

    nodes.forEach((node, i) => {
      const y = startY + i * (NODE_HEIGHT + V_GAP);
      const ln: LayoutNode = {
        node,
        layer: layerIdx,
        x,
        y,
        totalIn: inFlow.get(node.id) ?? 0,
        totalOut: outFlow.get(node.id) ?? 0,
      };
      layoutNodes.push(ln);
      layoutByID.set(node.id, ln);
    });
  }

  if (data.links.length === 0) {
    return { nodes: layoutNodes, links: [], svgHeight, stageHeaders };
  }

  const maxVal = Math.max(...data.links.map((l) => l.value));
  const minVal = Math.min(...data.links.map((l) => l.value));

  function scaledThickness(value: number): number {
    if (maxVal === minVal) return (MIN_LINK_THICKNESS + MAX_LINK_THICKNESS) / 2;
    const logVal = Math.log1p(value);
    const logMin = Math.log1p(minVal);
    const logMax = Math.log1p(maxVal);
    const t = (logVal - logMin) / (logMax - logMin);
    return MIN_LINK_THICKNESS + t * (MAX_LINK_THICKNESS - MIN_LINK_THICKNESS);
  }

  const sourcePortOffset = new Map<string, number>();
  const targetPortOffset = new Map<string, number>();

  const sortedLinks = [...data.links].sort((a, b) => b.value - a.value);
  const layoutLinks: LayoutLink[] = [];

  for (const link of sortedLinks) {
    const srcLayout = layoutByID.get(link.source);
    const tgtLayout = layoutByID.get(link.target);
    if (!srcLayout || !tgtLayout) continue;

    const thickness = scaledThickness(link.value);
    const srcOffset = sourcePortOffset.get(link.source) ?? 0;
    const tgtOffset = targetPortOffset.get(link.target) ?? 0;

    layoutLinks.push({
      link,
      sourceLayout: srcLayout,
      targetLayout: tgtLayout,
      thickness,
      sourceY: srcOffset,
      targetY: tgtOffset,
    });

    sourcePortOffset.set(link.source, srcOffset + thickness + 1);
    targetPortOffset.set(link.target, tgtOffset + thickness + 1);
  }

  return { nodes: layoutNodes, links: layoutLinks, svgHeight, stageHeaders };
}

function sankeyPath(
  srcX: number,
  srcY: number,
  tgtX: number,
  tgtY: number,
  thickness: number,
  srcNodeY: number,
  tgtNodeY: number,
): string {
  if (tgtX > srcX) {
    const x0 = srcX + NODE_WIDTH;
    const y0 = srcNodeY + NODE_HEIGHT / 2 + Math.min(8, Math.max(-8, srcY - 8));
    const x1 = tgtX;
    const y1 = tgtNodeY + NODE_HEIGHT / 2 + Math.min(8, Math.max(-8, tgtY - 8));

    const cx = (x0 + x1) / 2;
    const half = thickness / 2;

    const topPath = `M ${x0} ${y0 - half} C ${cx} ${y0 - half}, ${cx} ${y1 - half}, ${x1} ${y1 - half}`;
    const botPath = `L ${x1} ${y1 + half} C ${cx} ${y1 + half}, ${cx} ${y0 + half}, ${x0} ${y0 + half} Z`;

    return `${topPath} ${botPath}`;
  }

  const x0 = srcX + NODE_WIDTH;
  const y0 = srcNodeY + NODE_HEIGHT / 2;
  const x1 = tgtX + NODE_WIDTH;
  const y1 = tgtNodeY + NODE_HEIGHT / 2;
  const curveX = Math.max(x0, x1) + 40;
  const half = Math.max(2, thickness / 2);

  return `M ${x0} ${y0 - half} Q ${curveX} ${(y0 + y1) / 2}, ${x1} ${y1 - half} L ${x1} ${y1 + half} Q ${curveX} ${(y0 + y1) / 2}, ${x0} ${y0 + half} Z`;
}

interface Props {
  data: JourneyFlowResponse;
  width?: number;
  compact?: boolean;
}

export const JourneyFlowGraph: React.FC<Props> = ({
  data,
  width = 960,
  compact = false,
}) => {
  // Pan and Zoom Canvas State
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const dragInfoRef = useRef({ startX: 0, startY: 0, initialX: 0, initialY: 0, hasMoved: false });

  // Selection & Details Inspector State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLink, setSelectedLink] = useState<JourneyFlowLink | null>(null);

  // Hover & Tooltip State
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredLinkIdx, setHoveredLinkIdx] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<{ data: TooltipData; x: number; y: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const { nodes: layoutNodes, links: layoutLinks, svgHeight, stageHeaders } = useMemo(
    () => computeLayout(data, width, compact),
    [data, width, compact],
  );

  const activeFocusNodeId = selectedNodeId || hoveredNodeId;

  // Track incoming and outgoing links for the focused node
  const incomingLinkIndices = useMemo(() => {
    if (!activeFocusNodeId) return null;
    const set = new Set<number>();
    layoutLinks.forEach((ll, i) => {
      if (ll.link.target === activeFocusNodeId) {
        set.add(i);
      }
    });
    return set;
  }, [activeFocusNodeId, layoutLinks]);

  const outgoingLinkIndices = useMemo(() => {
    if (!activeFocusNodeId) return null;
    const set = new Set<number>();
    layoutLinks.forEach((ll, i) => {
      if (ll.link.source === activeFocusNodeId) {
        set.add(i);
      }
    });
    return set;
  }, [activeFocusNodeId, layoutLinks]);

  // Zoom handlers
  const handleZoom = useCallback((delta: number) => {
    setTransform((prev) => {
      const newScale = Math.min(2.5, Math.max(0.6, prev.scale + delta));
      return { ...prev, scale: Number(newScale.toFixed(2)) };
    });
  }, []);

  const handleResetView = useCallback(() => {
    setTransform({ x: 0, y: 0, scale: 1 });
    setSelectedNodeId(null);
    setSelectedLink(null);
  }, []);

  // Wheel zoom handler: ONLY zoom when Ctrl is pressed to preserve normal page scroll
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const zoomFactor = e.deltaY < 0 ? 0.15 : -0.15;
        setTransform((prev) => {
          const newScale = Math.min(2.5, Math.max(0.6, prev.scale + zoomFactor));
          return { ...prev, scale: Number(newScale.toFixed(2)) };
        });
      }
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // Mouse pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragInfoRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialX: transform.x,
      initialY: transform.y,
      hasMoved: false,
    };
  }, [transform]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        const dx = e.clientX - dragInfoRef.current.startX;
        const dy = e.clientY - dragInfoRef.current.startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          dragInfoRef.current.hasMoved = true;
        }
        setTransform((prev) => ({
          ...prev,
          x: dragInfoRef.current.initialX + dx,
          y: dragInfoRef.current.initialY + dy,
        }));
      } else if (tooltip) {
        setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null));
      }
    },
    [isDragging, tooltip],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Background click: deselect if we weren't dragging
  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    if (dragInfoRef.current.hasMoved) {
      dragInfoRef.current.hasMoved = false;
      return;
    }
    const target = e.target as HTMLElement;
    if (target.tagName === 'svg' || target.id === 'canvas-bg' || target.classList.contains('canvas-area')) {
      setSelectedNodeId(null);
      setSelectedLink(null);
    }
  }, []);

  // Node selection click
  const handleNodeClick = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (dragInfoRef.current.hasMoved) {
      dragInfoRef.current.hasMoved = false;
      return;
    }
    setSelectedLink(null);
    setSelectedNodeId((prev) => (prev === nodeId ? null : nodeId));
  }, []);

  // Link selection click
  const handleLinkClick = useCallback((link: JourneyFlowLink, e: React.MouseEvent) => {
    e.stopPropagation();
    if (dragInfoRef.current.hasMoved) {
      dragInfoRef.current.hasMoved = false;
      return;
    }
    setSelectedNodeId(null);
    setSelectedLink((prev) =>
      prev?.source === link.source && prev?.target === link.target ? null : link,
    );
  }, []);

  const handleNodeMouseEnter = useCallback(
    (ln: LayoutNode, e: React.MouseEvent) => {
      setHoveredNodeId(ln.node.id);
      setHoveredLinkIdx(null);
      if (!selectedNodeId && !selectedLink) {
        setTooltip({
          x: e.clientX,
          y: e.clientY,
          data: {
            kind: 'node',
            label: ln.node.label,
            type: ln.node.type as any,
            incomingJourneys: ln.totalIn,
            outgoingJourneys: ln.totalOut,
            totalJourneys: data.total_journeys,
            convertedJourneys: data.converted_journeys,
          },
        });
      }
    },
    [data.total_journeys, data.converted_journeys, selectedNodeId, selectedLink],
  );

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNodeId(null);
    setTooltip(null);
  }, []);

  const handleLinkMouseEnter = useCallback(
    (ll: LayoutLink, idx: number, e: React.MouseEvent) => {
      setHoveredLinkIdx(idx);
      setHoveredNodeId(null);
      if (!selectedNodeId && !selectedLink) {
        const srcLabel =
          layoutNodes.find((n) => n.node.id === ll.link.source)?.node.label ?? ll.link.source;
        const tgtLabel =
          layoutNodes.find((n) => n.node.id === ll.link.target)?.node.label ?? ll.link.target;
        setTooltip({
          x: e.clientX,
          y: e.clientY,
          data: {
            kind: 'link',
            fromLabel: srcLabel,
            toLabel: tgtLabel,
            journeyCount: ll.link.value,
            totalJourneys: data.total_journeys,
          },
        });
      }
    },
    [layoutNodes, data.total_journeys, selectedNodeId, selectedLink],
  );

  const handleLinkMouseLeave = useCallback(() => {
    setHoveredLinkIdx(null);
    setTooltip(null);
  }, []);

  if (data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-gray-400 font-mono">
        No journey flow data available for selected criteria.
      </div>
    );
  }

  const containerHeight = compact ? Math.max(260, svgHeight) : Math.max(380, svgHeight + 20);

  return (
    <div className="relative w-full overflow-x-auto rounded-2xl">
      <div
        ref={containerRef}
        className={`relative w-full min-w-[680px] overflow-hidden rounded-2xl bg-[#FAF9F5] border border-gray-200/90 select-none shadow-xs ${
          isDragging ? 'cursor-grabbing' : 'cursor-grab'
        }`}
        style={{ height: containerHeight }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleCanvasClick}
        role="region"
        aria-label="Interactive customer journey progression network map"
      >
        {/* Subtle Architectural Dot Grid Pattern */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none opacity-30 canvas-area"
          id="canvas-bg"
        >
          <defs>
            <pattern id="canvas-grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="#94A3B8" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#canvas-grid)" />
        </svg>

        {/* Floating Canvas Navigation Toolbar */}
        <div
          className="absolute top-3 right-3 z-30 flex items-center gap-1 p-1 bg-white/95 backdrop-blur-md rounded-xl border border-gray-200/80 shadow-xs"
          role="toolbar"
          aria-label="Canvas zoom controls"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => handleZoom(0.2)}
            className="p-1.5 rounded-lg text-gray-600 hover:text-graphite-950 hover:bg-gray-100 transition-colors"
            title="Zoom In (+)"
            aria-label="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <span className="text-[11px] font-mono font-bold text-graphite-800 px-1.5 min-w-[44px] text-center">
            {Math.round(transform.scale * 100)}%
          </span>
          <button
            onClick={() => handleZoom(-0.2)}
            className="p-1.5 rounded-lg text-gray-600 hover:text-graphite-950 hover:bg-gray-100 transition-colors"
            title="Zoom Out (-)"
            aria-label="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="w-[1px] h-4 bg-gray-200 mx-0.5" />
          <button
            onClick={handleResetView}
            className="p-1.5 rounded-lg text-gray-500 hover:text-coral-600 hover:bg-gray-100 transition-colors"
            title="Reset Canvas View"
            aria-label="Reset Canvas View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Canvas Interaction Prompt Pill */}
        {!compact && (
          <div className="absolute bottom-3 left-3 z-20 hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/90 backdrop-blur-xs border border-gray-200/80 text-[10.5px] font-mono text-gray-500 pointer-events-none shadow-2xs">
            <Move className="w-3.5 h-3.5 text-gray-400" />
            <span>Drag to pan · Ctrl + scroll to zoom · Click node or link to inspect</span>
          </div>
        )}

        {/* Main SVG Canvas */}
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${svgHeight}`}
          className="overflow-visible canvas-area"
          role="img"
          aria-label="Directional customer journey network visualization"
        >
          <g
            transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}
            style={{
              transformOrigin: `${width / 2}px ${svgHeight / 2}px`,
              transition: isDragging ? 'none' : 'transform 0.08s ease-out',
            }}
          >
            {/* Stage Column Headers */}
            <g className="stage-headers pointer-events-none">
              {stageHeaders.map((sh, idx) => (
                <g key={idx} transform={`translate(${sh.x}, 24)`}>
                  <text
                    textAnchor="middle"
                    fill="#0F172A"
                    fontSize="11"
                    fontFamily="'Plus Jakarta Sans', system-ui, sans-serif"
                    fontWeight="700"
                    letterSpacing="0.04em"
                    className="uppercase"
                  >
                    {sh.label}
                  </text>
                  <text
                    y="14"
                    textAnchor="middle"
                    fill="#64748B"
                    fontSize="9.5"
                    fontFamily="'Plus Jakarta Sans', system-ui, sans-serif"
                  >
                    {sh.sublabel}
                  </text>
                </g>
              ))}
            </g>

            {/* Links (Ribbons) — Slate with controlled opacity; Active = JourneyIQ Coral */}
            <g aria-label="Journey transitions">
              {layoutLinks.map((ll, idx) => {
                const src = ll.sourceLayout;
                const tgt = ll.targetLayout;
                const path = sankeyPath(src.x, src.y, tgt.x, tgt.y, ll.thickness, src.y, tgt.y);

                const isLinkSelected =
                  selectedLink?.source === ll.link.source && selectedLink?.target === ll.link.target;
                const isIncomingToActive = incomingLinkIndices?.has(idx) ?? false;
                const isOutgoingFromActive = outgoingLinkIndices?.has(idx) ?? false;
                const isConnected = isIncomingToActive || isOutgoingFromActive;
                const isHovered = hoveredLinkIdx === idx;

                // Base style: Slate with controlled opacity
                let opacity = 0.24;
                let fillColor = '#94A3B8';

                if (tgt.node.id === CONVERSION_ID) {
                  fillColor = '#64748B';
                  opacity = 0.32;
                } else if (src.node.id === START_ID) {
                  fillColor = '#94A3B8';
                  opacity = 0.26;
                }

                // Focus / Highlight states
                if (activeFocusNodeId) {
                  if (isConnected) {
                    // Active links highlight in JourneyIQ Coral
                    opacity = 0.88;
                    fillColor = tgt.node.id === CONVERSION_ID ? '#059669' : '#FF5722';
                  } else {
                    // Dim unrelated links
                    opacity = 0.04;
                  }
                } else if (selectedLink) {
                  if (isLinkSelected) {
                    opacity = 0.92;
                    fillColor = tgt.node.id === CONVERSION_ID ? '#059669' : '#FF5722';
                  } else {
                    opacity = 0.04;
                  }
                } else if (isHovered) {
                  opacity = 0.92;
                  fillColor = tgt.node.id === CONVERSION_ID ? '#059669' : '#FF5722';
                }

                return (
                  <path
                    key={idx}
                    d={path}
                    fill={fillColor}
                    opacity={opacity}
                    style={{
                      transition: 'opacity 0.15s ease, fill 0.15s ease',
                      cursor: 'pointer',
                    }}
                    onClick={(e) => handleLinkClick(ll.link, e)}
                    onMouseEnter={(e) => handleLinkMouseEnter(ll, idx, e)}
                    onMouseLeave={handleLinkMouseLeave}
                  />
                );
              })}
            </g>

            {/* Nodes — White / Graphite serious design system */}
            <g aria-label="Journey channel nodes">
              {layoutNodes.map((ln) => {
                const isSelected = selectedNodeId === ln.node.id;
                const isHovered = hoveredNodeId === ln.node.id;
                const isStart = ln.node.type === 'start';
                const isConv = ln.node.type === 'conversion';

                const isConnected =
                  activeFocusNodeId !== null &&
                  layoutLinks.some(
                    (ll) =>
                      (ll.link.source === activeFocusNodeId && ll.link.target === ln.node.id) ||
                      (ll.link.target === activeFocusNodeId && ll.link.source === ln.node.id),
                  );

                const isDimmed = activeFocusNodeId !== null && !isSelected && !isHovered && !isConnected;
                const opacity = isDimmed ? 0.2 : 1;

                // Color tokens according to specifications:
                // Start: Graphite (#0F172A)
                // Channel: White (#FFFFFF)
                // Conversion: Emerald (#F0FDF4)
                let nodeBg = '#FFFFFF';
                let nodeBorder = '#CBD5E1';
                let labelColor = '#0F172A';
                let sublabelColor = '#64748B';

                if (isStart) {
                  nodeBg = '#0F172A';
                  nodeBorder = '#334155';
                  labelColor = '#FFFFFF';
                  sublabelColor = '#94A3B8';
                } else if (isConv) {
                  nodeBg = '#F0FDF4';
                  nodeBorder = '#10B981';
                  labelColor = '#065F46';
                  sublabelColor = '#047857';
                }

                return (
                  <g
                    key={ln.node.id}
                    transform={`translate(${ln.x}, ${ln.y})`}
                    style={{ transition: 'opacity 0.15s ease', opacity, cursor: 'pointer' }}
                    onClick={(e) => handleNodeClick(ln.node.id, e)}
                    onMouseEnter={(e) => handleNodeMouseEnter(ln, e)}
                    onMouseLeave={handleNodeMouseLeave}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    aria-label={`${ln.node.label}: ${ln.totalIn} in, ${ln.totalOut} out. Click to inspect.`}
                  >
                    {/* Active / Hovered Focus Ring */}
                    {(isSelected || isHovered) && (
                      <rect
                        x={-3}
                        y={-3}
                        width={NODE_WIDTH + 6}
                        height={NODE_HEIGHT + 6}
                        rx={NODE_RADIUS + 3}
                        fill="none"
                        stroke={isSelected ? '#FF5722' : isConv ? '#059669' : '#FF5722'}
                        strokeWidth={2}
                      />
                    )}

                    {/* Main Node Box */}
                    <rect
                      width={NODE_WIDTH}
                      height={NODE_HEIGHT}
                      rx={NODE_RADIUS}
                      fill={nodeBg}
                      stroke={nodeBorder}
                      strokeWidth={isConv ? 1.5 : 1}
                      filter="drop-shadow(0 1px 2px rgba(15, 23, 42, 0.05))"
                    />

                    {/* Node Label */}
                    <text
                      x={NODE_WIDTH / 2}
                      y={NODE_HEIGHT / 2 - 4}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fill={labelColor}
                      fontSize="11.5"
                      fontFamily="'Plus Jakarta Sans', system-ui, sans-serif"
                      fontWeight="700"
                      style={{ pointerEvents: 'none' }}
                    >
                      {ln.node.label.length > 17
                        ? ln.node.label.slice(0, 16) + '…'
                        : ln.node.label}
                    </text>

                    {/* Flow volume indicator */}
                    <text
                      x={NODE_WIDTH / 2}
                      y={NODE_HEIGHT / 2 + 9}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fill={sublabelColor}
                      fontSize="9"
                      fontFamily="'JetBrains Mono', monospace"
                      fontWeight="500"
                      style={{ pointerEvents: 'none' }}
                    >
                      {isStart
                        ? `${data.total_journeys.toLocaleString()} entries`
                        : isConv
                        ? `${data.converted_journeys.toLocaleString()} converted`
                        : `${Math.max(ln.totalIn, ln.totalOut).toLocaleString()} journeys`}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>
        </svg>

        {/* Floating Details Inspector Panel (Only when a node or link is selected) */}
        {!compact && (selectedNodeId || selectedLink) && (
          <div
            className="absolute top-12 right-3 z-40"
            onClick={(e) => e.stopPropagation()}
          >
            <JourneyFlowInspector
              selectedNodeId={selectedNodeId}
              selectedLink={selectedLink}
              data={data}
              onClose={() => {
                setSelectedNodeId(null);
                setSelectedLink(null);
              }}
            />
          </div>
        )}

        {/* Hover Tooltip (Only when nothing is clicked) */}
        {!selectedNodeId && !selectedLink && tooltip && (
          <JourneyFlowTooltip data={tooltip.data} x={tooltip.x} y={tooltip.y} />
        )}
      </div>
    </div>
  );
};
