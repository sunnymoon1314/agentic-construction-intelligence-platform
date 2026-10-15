#!/usr/bin/env python3
"""
ACIP S04: Multi-Agent Delay Deliberation CLI Client
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: agent_client/client.py

CLI entrypoint for running the 3-Agent Adversarial Deliberation Protocol.
"""
import argparse
import os
import sys

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if S04_ROOT not in sys.path:
    sys.path.insert(0, S04_ROOT)

from agent_client.deliberation_pipeline import DeliberationPipeline


def main():
    parser = argparse.ArgumentParser(description="ACIP S04 Multi-Agent Delay Deliberation Client")
    parser.add_argument("--project-id", default="PRJ-WHC-COM-001", help="Project ID")
    parser.add_argument("--event-id", default="DLY-2026-001", help="Delay Event ID")
    parser.add_argument("--generate-memo", action="store_true", help="Generate executive EOT memo")
    args = parser.parse_args()

    print("=" * 80)
    print("ACIP S04: Multi-Agent Delay Deliberation Client")
    print("=" * 80)
    print(f"[*] Target Project: {args.project_id}")
    print(f"[*] Delay Event:   {args.event_id}")

    pipeline = DeliberationPipeline()
    consensus = pipeline.run_deliberation(
        project_id=args.project_id,
        event_id=args.event_id,
        persist_log=True,
    )

    print("\n" + "=" * 80)
    print("STATUTORY CONSENSUS DETERMINATION")
    print("=" * 80)
    print(f"Session ID:                     {consensus.session_id}")
    print(f"Event Title:                    {consensus.event_title}")
    print(f"Determination Tier:             {consensus.determination_tier}")
    print(f"Net Critical Delay:             {consensus.net_critical_delay_workdays} workdays")
    print(f"Candidate EOT Relief:           {consensus.candidate_eot_relief_days} workdays")
    print(f"Contractor Culpable Delay:      {consensus.contractor_culpable_days} workdays")
    print(f"Liquidated Damages Exposure:    S$ {consensus.liquidated_damages_exposure_sgd:,.2f}")
    print(f"Concurrency Attribution:        {consensus.concurrency_attribution}")
    print(f"Notice Condition Precedent:     {consensus.notice_compliance_status}")
    print(f"Advisory Legal Disclaimer:      {consensus.adjudication_disclaimer}")

    print("\n--- DELIBERATION TURNS ---")
    for t in consensus.turns:
        print(f"\n[Round {t.round_number}] {t.agent_name} ({t.agent_role}):")
        print(f"  Position: {t.position_statement[:120]}...")
        print(f"  Tool Invoked: {t.tool_invoked}")
        print(f"  Recommended EOT: {t.recommended_eot_days} workdays | LD: S$ {t.recommended_ld_exposure_sgd:,.2f}")

    if args.generate_memo:
        print("\n" + "=" * 80)
        print("EXECUTIVE DELAY DISPUTE & EOT MEMO (SYNTHESIS)")
        print("=" * 80)
        print(f"Project:     {args.project_id}")
        print(f"Event:       {args.event_id} - {consensus.event_title}")
        print(f"Assessment:  {consensus.determination_tier}")
        print(f"Finding:     Critical delay of {consensus.net_critical_delay_workdays} days evaluated.")
        print(f"EOT Relief:  {consensus.candidate_eot_relief_days} days granted.")
        print(f"LD Exposure: S$ {consensus.liquidated_damages_exposure_sgd:,.2f}.")
        print("=" * 80)


if __name__ == "__main__":
    main()
