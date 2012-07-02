<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

<dot>
digraph {
        node [shape="record"];

        y [label="{<mask>mask:64|<0>0|<1>1|<2>2|<3>3|<4>4|...|63}"];
}
</dot>

<dot>
digraph {
        
        node [shape="record"];

        root [label="{Map|<st>SubTrie}"];
        leaf [label="{<s>Map|SubTrie}|{Map|SubTrie}|{Map|SubTrie}|{Map|SubTrie}"];


        root:st -> leaf:s;
        
}
</dot>


ads
<dot>
digraph {
        node [shape="record"];

ex [label="{<mask>bitmask}|{<0>0|<1>1|<2>2|<3>3|<4>4|...}"];

                
        root [label="{<mask>bitmask}|{<0>|<1>|<2>|<3>|<4>|<5>|<6>|<7>}"];

        leaf1 [label="{<mask>bitmask}|{<0>|<1>|<2>|<3>|<4>|<5>|<6>|<7>}"];
        leaf2 [label="{<mask>bitmask}|{<0>0:leaf|<3>3:value|<32>32:leaf}"];
        
        root:0 -> root:1;
        leaf1:1 -> leaf2;
}
</dot>


</%block>
</article>
