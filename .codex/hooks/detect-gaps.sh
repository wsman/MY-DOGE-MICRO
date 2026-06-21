#!/bin/bash
# Hook: detect-gaps.sh
# Event: SessionStart
# Purpose: Detect missing documentation when code/prototypes exist
# Cross-platform: Windows Git Bash compatible (uses grep -E, not -P)

# Exit on error for debugging (but don't fail the session)
set +e

echo "=== Checking for Documentation Gaps ==="

# --- Check 0: Fresh project detection (suggests /constitute) ---
FRESH_PROJECT=true

# Check if engine or product stack is configured
if [ -f "standards/technical-preferences.md" ]; then
  TECH_LINE=$(grep -E "^[[:space:]]*(-[[:space:]]*)?\*\*(Engine|Language|Framework|Stack)\*\*:" standards/technical-preferences.md 2>/dev/null)
  if [ -n "$TECH_LINE" ] && ! echo "$TECH_LINE" | grep -Eq "TO BE CONFIGURED|Not selected|TBD|\\[.*\\]" 2>/dev/null; then
    FRESH_PROJECT=false
  fi
fi

# Check if game or product concept exists
if [ -f "design/cdd/game-concept.md" ] || [ -f "design/cdd/product-concept.md" ]; then
  FRESH_PROJECT=false
fi

# Check if source code exists
if [ -d "src" ]; then
  SRC_CHECK=$(find src -type f \( -name "*.gd" -o -name "*.cs" -o -name "*.cpp" -o -name "*.c" -o -name "*.h" -o -name "*.hpp" -o -name "*.rs" -o -name "*.py" -o -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" -o -name "*.java" -o -name "*.rb" -o -name "*.php" -o -name "*.swift" -o -name "*.kt" \) 2>/dev/null | head -1)
  if [ -n "$SRC_CHECK" ]; then
    FRESH_PROJECT=false
  fi
fi

if [ "$FRESH_PROJECT" = true ]; then
  echo ""
  echo "🚀 NEW PROJECT: No technology configured, no concept document, no source code."
  echo "   This looks like a fresh start! Run: /constitute"
  echo ""
  echo "💡 To get a comprehensive project analysis, run: /project-stage-detect"
  echo "==================================="
  exit 0
fi

# --- Check 1: Substantial codebase but sparse design docs ---
if [ -d "src" ]; then
  # Count source files (cross-platform, handles Windows paths)
  SRC_FILES=$(find src -type f \( -name "*.gd" -o -name "*.cs" -o -name "*.cpp" -o -name "*.c" -o -name "*.h" -o -name "*.hpp" -o -name "*.rs" -o -name "*.py" -o -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" -o -name "*.java" -o -name "*.rb" -o -name "*.php" -o -name "*.swift" -o -name "*.kt" \) 2>/dev/null | wc -l)
else
  SRC_FILES=0
fi

if [ -d "design/cdd" ]; then
  DESIGN_FILES=$(find design/cdd -type f -name "*.md" 2>/dev/null | wc -l)
else
  DESIGN_FILES=0
fi

# Normalize whitespace from wc output
SRC_FILES=$(echo "$SRC_FILES" | tr -d ' ')
DESIGN_FILES=$(echo "$DESIGN_FILES" | tr -d ' ')

if [ "$SRC_FILES" -gt 50 ] && [ "$DESIGN_FILES" -lt 5 ]; then
  echo "⚠️  GAP: Substantial codebase ($SRC_FILES source files) but sparse design docs ($DESIGN_FILES files)"
  echo "    Suggested action: /reverse-document design src/[system]"
  echo "    Or run: /project-stage-detect to get full analysis"
fi

# --- Check 2: Prototypes without documentation ---
if [ -d "prototypes" ]; then
  PROTOTYPE_DIRS=$(find prototypes -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
  UNDOCUMENTED_PROTOS=()

  if [ -n "$PROTOTYPE_DIRS" ]; then
    while IFS= read -r proto_dir; do
      # Normalize path separators for Windows
      proto_dir=$(echo "$proto_dir" | sed 's|\\|/|g')

      # Check for README.md or CONCEPT.md
      if [ ! -f "${proto_dir}/README.md" ] && [ ! -f "${proto_dir}/CONCEPT.md" ]; then
        proto_name=$(basename "$proto_dir")
        UNDOCUMENTED_PROTOS+=("$proto_name")
      fi
    done <<< "$PROTOTYPE_DIRS"

    if [ ${#UNDOCUMENTED_PROTOS[@]} -gt 0 ]; then
      echo "⚠️  GAP: ${#UNDOCUMENTED_PROTOS[@]} undocumented prototype(s) found:"
      for proto in "${UNDOCUMENTED_PROTOS[@]}"; do
        echo "    - prototypes/$proto/ (no README or CONCEPT doc)"
      done
      echo "    Suggested action: /reverse-document concept prototypes/[name]"
    fi
  fi
fi

# --- Check 3: Core systems without architecture docs ---
if [ -d "src/core" ] || [ -d "src/engine" ] || [ -d "src/api" ] || [ -d "src/cli" ] || [ -d "src/services" ]; then
  if [ ! -d "docs/architecture" ]; then
    echo "⚠️  GAP: Core engine/product systems exist but no docs/architecture/ directory"
    echo "    Suggested action: Create docs/architecture/ and run /architecture-decision"
  else
    ADR_COUNT=$(find docs/architecture -type f -name "*.md" 2>/dev/null | wc -l)
    ADR_COUNT=$(echo "$ADR_COUNT" | tr -d ' ')

    if [ "$ADR_COUNT" -lt 3 ]; then
      echo "⚠️  GAP: Core systems exist but only $ADR_COUNT ADR(s) documented"
      echo "    Suggested action: /reverse-document architecture src/core/[system]"
    fi
  fi
fi

# --- Check 4: Gameplay systems without design docs ---
if [ -d "src/gameplay" ]; then
  # Find major gameplay subdirectories (those with 5+ files)
  GAMEPLAY_SYSTEMS=$(find src/gameplay -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

  if [ -n "$GAMEPLAY_SYSTEMS" ]; then
    while IFS= read -r system_dir; do
      system_dir=$(echo "$system_dir" | sed 's|\\|/|g')
      system_name=$(basename "$system_dir")
      file_count=$(find "$system_dir" -type f 2>/dev/null | wc -l)
      file_count=$(echo "$file_count" | tr -d ' ')

      # If system has 5+ files, check for corresponding design doc
      if [ "$file_count" -ge 5 ]; then
        # Check for design doc (allow variations: combat-system.md, combat.md)
        design_doc_1="design/cdd/${system_name}-system.md"
        design_doc_2="design/cdd/${system_name}.md"

        if [ ! -f "$design_doc_1" ] && [ ! -f "$design_doc_2" ]; then
          echo "⚠️  GAP: Gameplay system 'src/gameplay/$system_name/' ($file_count files) has no design doc"
          echo "    Expected: design/cdd/${system_name}-system.md or design/cdd/${system_name}.md"
          echo "    Suggested action: /reverse-document design src/gameplay/$system_name"
        fi
      fi
    done <<< "$GAMEPLAY_SYSTEMS"
  fi
fi

# --- Check 4b: Product modules without CDD/module docs ---
if [ -d "src" ]; then
  PRODUCT_SYSTEMS=$(find src -mindepth 1 -maxdepth 2 -type d 2>/dev/null | grep -E '(^src/(api|cli|commands|routes|web|app|data|db|migrations|services)$|/(api|cli|commands|routes|migrations|services)$)' || true)

  if [ -n "$PRODUCT_SYSTEMS" ]; then
    while IFS= read -r product_dir; do
      product_dir=$(echo "$product_dir" | sed 's|\\|/|g')
      module_name=$(basename "$product_dir")
      file_count=$(find "$product_dir" -type f 2>/dev/null | wc -l)
      file_count=$(echo "$file_count" | tr -d ' ')

      if [ "$file_count" -ge 5 ]; then
        design_doc_1="design/cdd/${module_name}-module.md"
        design_doc_2="design/cdd/${module_name}-service.md"
        design_doc_3="design/cdd/${module_name}.md"

        if [ ! -f "$design_doc_1" ] && [ ! -f "$design_doc_2" ] && [ ! -f "$design_doc_3" ]; then
          echo "⚠️  GAP: Product module '$product_dir/' ($file_count files) has no CDD/module doc"
          echo "    Expected: design/cdd/${module_name}-module.md, design/cdd/${module_name}-service.md, or design/cdd/${module_name}.md"
          echo "    Suggested action: /reverse-document design $product_dir"
        fi
      fi
    done <<< "$PRODUCT_SYSTEMS"
  fi
fi

# --- Check 5: Production planning ---
if [ "$SRC_FILES" -gt 100 ]; then
  # For projects with substantial code, check for production planning
  if [ ! -d "production/sprints" ] && [ ! -d "production/milestones" ]; then
    echo "⚠️  GAP: Large codebase ($SRC_FILES files) but no production planning found"
    echo "    Suggested action: /sprint-plan or create production/ directory"
  fi
fi

# --- Summary ---
echo ""
echo "💡 To get a comprehensive project analysis, run: /project-stage-detect"
echo "==================================="

exit 0
