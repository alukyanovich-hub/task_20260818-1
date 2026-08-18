"""Transaction categorisation.

Two categorisers implement the same `categorize_batch(descriptions) ->
dict[str, str]` interface:

- `OpenAICategorizer` calls the OpenAI API (see docs/AI_PROMPTS.md for
  the exact prompt) and is used whenever `OPENAI_API_KEY` is set.
- `KeywordCategorizer` is a deterministic substring-match fallback, used
  when no API key is configured, and also as a safety net if the AI call
  itself fails (bad response, timeout, rate limit, etc.) so a transaction
  is never left without a category.

`categorize_batch` takes a batch rather than a single description because
the CSV import path reuses it: many rows in real bank exports repeat the
same handful of merchant descriptions, so callers pass the *unique*
descriptions once and fan the result back out to every row, instead of
paying for one AI call per row.
"""
import json
import logging

from django.conf import settings

from apps.transactions.models import Category

logger = logging.getLogger(__name__)

_LABEL_TO_VALUE = {label.lower(): value for value, label in Category.choices}

PROMPT_TEMPLATE = """You are a banking-transaction categorisation engine.

Classify each transaction description below into exactly one of these 10 categories:
Groceries, Dining Out, Utilities, Transportation, Entertainment, Healthcare, Shopping, Housing, Education, Miscellaneous.

Rules:
- Pick exactly one category per transaction, using the category name exactly as written above.
- Use "Miscellaneous" only when none of the other 9 categories clearly apply (e.g. generic bank transfers, salary payments, tax refunds, ATM withdrawals).
- Respond with ONLY a JSON object mapping each transaction description (verbatim, exactly as given) to its category name. No prose, no markdown code fences, no extra keys.

Transactions:
{numbered_descriptions}
"""
# ^ Sent as-is to the model; OpenAI's JSON response_format mode enforces
# the "only JSON" instruction server-side, but the wording is kept
# explicit so the same prompt/parsing logic would degrade gracefully
# against a provider without a JSON mode.


def build_prompt(descriptions):
    numbered = '\n'.join(f'{i}. "{d}"' for i, d in enumerate(descriptions, start=1))
    return PROMPT_TEMPLATE.format(numbered_descriptions=numbered)


class KeywordCategorizer:
    source = 'rule'

    _RULES = (
        (Category.GROCERIES, ('albert heijn', 'ah online', 'grocery', 'groceries', 'supermarket')),
        (Category.DINING_OUT, ('restaurant', 'dining', 'cafe', 'coffee shop')),
        (Category.UTILITIES, (
            'eneco', 'energy bill', 'ziggo', 't-mobile', 'mobile bill', 'phone bill',
            'internet bill', 'water bill', 'electricity bill', 'gas bill',
        )),
        (Category.TRANSPORTATION, (
            'ns train', 'train ticket', 'car lease', 'fuel', 'gas station',
            'parking', 'uber', 'taxi', 'public transport',
        )),
        (Category.ENTERTAINMENT, ('netflix', 'spotify', 'cinema', 'movie theatre', 'concert')),
        (Category.HEALTHCARE, ('pharmacy', 'doctor', 'hospital', 'dental', 'clinic')),
        (Category.SHOPPING, ('bol.com', 'amazon', 'ideal payment', 'zalando', 'shopping')),
        (Category.HOUSING, ('rent payment', 'municipal tax', 'mortgage')),
        (Category.EDUCATION, ('tuition', 'university', 'school fee', 'course fee')),
    )

    def categorize_batch(self, descriptions):
        return {description: self._categorize_one(description) for description in descriptions}

    def _categorize_one(self, description):
        lowered = description.lower()
        for category, keywords in self._RULES:
            if any(keyword in lowered for keyword in keywords):
                return category
        return Category.MISCELLANEOUS


class OpenAICategorizer:
    source = 'ai'

    def __init__(self):
        import openai

        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL
        self._fallback = KeywordCategorizer()

    def categorize_batch(self, descriptions):
        descriptions = list(dict.fromkeys(descriptions))  # de-dupe, keep order
        if not descriptions:
            return {}
        try:
            return self._categorize_via_ai(descriptions)
        except Exception:
            logger.exception('OpenAI categorisation failed, falling back to keyword rules')
            return self._fallback.categorize_batch(descriptions)

    def _categorize_via_ai(self, descriptions):
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={'type': 'json_object'},
            messages=[{'role': 'user', 'content': build_prompt(descriptions)}],
        )
        mapping = json.loads(response.choices[0].message.content)

        result = {}
        for description in descriptions:
            label = str(mapping.get(description, '')).strip().lower()
            result[description] = _LABEL_TO_VALUE.get(label, Category.MISCELLANEOUS)
        return result


def get_categorizer():
    if settings.OPENAI_API_KEY:
        return OpenAICategorizer()
    return KeywordCategorizer()
