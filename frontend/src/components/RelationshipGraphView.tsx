"use client";

import React, { useEffect, useState, useCallback } from "react";
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge
} from "reactflow";
import "reactflow/dist/style.css";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import { GitFork, AlertCircle, RefreshCw, Layers } from "lucide-react";

interface RelationshipGraphViewProps {
  lang: Language;
  onSelectFDR: (id: number) => void;
}

export function RelationshipGraphView({ lang, onSelectFDR }: RelationshipGraphViewProps) {
  const t = translations[lang];
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [graphMetrics, setGraphMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getGraph();
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
      setGraphMetrics(data.graph_metrics || null);
    } catch (err) {
      console.error("Failed to load graph:", err);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const onNodeClick = (_: any, node: Node) => {
    if (node.data?.node_type === "FDR") {
      const fdrId = parseInt(node.id.replace("fdr_", ""), 10);
      if (!isNaN(fdrId)) {
        onSelectFDR(fdrId);
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Controls & Anomaly Summary */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900 text-sm flex items-center">
            <GitFork className="w-4 h-4 mr-1.5 text-aicte-navy" />
            AICTE Entity Relationship Graph (NetworkX + React Flow)
          </h3>
          <p className="text-xs text-slate-500">
            Traces multi-entity links: Societies &rarr; Institutions &rarr; FDRs &rarr; Banks &rarr; Signatories.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 rounded bg-[#1B365D]"></span>
            <span className="text-slate-600">Standard</span>
            <span className="inline-block w-3 h-3 rounded bg-[#DC2626] ml-2"></span>
            <span className="text-slate-600">High Risk FDR</span>
            <span className="inline-block w-3 h-3 rounded bg-[#FF9933] ml-2"></span>
            <span className="text-slate-600">Cross-Institution Signatory</span>
          </div>
          <button
            onClick={loadGraph}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 transition"
            title="Reload Graph"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Anomaly Callout if detected */}
      {graphMetrics?.anomalies_detected > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span className="text-amber-900">
            <strong>Graph Intelligence Alert:</strong> {graphMetrics.anomalies_detected} entity connection(s) identified (e.g. shared trust or signatory operating across multiple institutions).
          </span>
        </div>
      )}

      {/* Canvas */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm h-[600px] overflow-hidden relative">
        {loading ? (
          <div className="flex items-center justify-center h-full text-slate-400 text-xs">
            Synthesizing NetworkX layout...
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
          >
            <Background color="#cbd5e1" gap={16} />
            <Controls />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}

